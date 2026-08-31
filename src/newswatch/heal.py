"""Repair a crawl source's CSS selectors when a site changes its HTML.

Per-source selectors are precise but brittle. When a source's ``item`` selector stops
matching (its listing still fetches fine but yields zero rows for two consecutive
polls), this fetches the listing, asks an LLM for fresh selectors, and — crucially —
validates the candidates by re-running extraction against the same HTML. Only
selectors that actually extract multiple rows with non-empty title and link are
accepted and written back to ``sources.toml``; the change is reported so a human can
review it. Selectors that do not extract are never written."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import requests
from thinchat.errors import ThinchatError

from newswatch._llm import DEFAULT_PROVIDER, make_llm_client, scrub_exception, scrub_secrets
from newswatch.crawl import extract_items
from newswatch.errors import HealError, NewswatchError
from newswatch.http import get
from newswatch.robots import RobotsGate
from newswatch.sources import Source, update_selectors
from newswatch.state import State

__all__ = ["HEAL_THRESHOLD", "HealResult", "needs_heal", "heal_source",
           "heal_empty_sources", "propose_selectors"]

HEAL_THRESHOLD = 2
_MIN_VALID_ROWS = 2
_MAX_TOKENS = 400
_SYSTEM = (
    "You are given the HTML of a news listing page. Return ONLY a JSON object with "
    "keys item, title, link, date giving CSS selectors that select, respectively: "
    "each article row; the headline element within a row; the link within a row "
    "(use the form 'selector@href' to read an href attribute); and the date element "
    "within a row (or empty string if none). No prose, no code fences."
)
_SELECTOR_KEYS = ("item", "title", "link", "date")


@dataclass(frozen=True, slots=True, kw_only=True)
class HealResult:
    """The outcome of a heal attempt on one source: the ``old`` and proposed ``new``
    selector maps, whether the new ones were ``applied`` (validated and written), and a
    human ``note`` for the digest/log."""

    source_name: str
    old:         dict[str, str]
    new:         dict[str, str]
    applied:     bool
    note:        str


def needs_heal(source: Source, state: State) -> bool:
    """Whether ``source`` is a crawl source that has hit the empty-poll threshold."""
    return (source.kind == "crawl"
            and state.empty_polls_by_source.get(source.name, 0) >= HEAL_THRESHOLD)


def heal_source(
    source: Source, *, gate: RobotsGate | None, session: requests.Session | None = None,
    apply: bool = True, path: Path | None = None,
    provider: str = DEFAULT_PROVIDER, model: str | None = None, api_key: str | None = None,
) -> HealResult | None:
    """Attempt to repair ``source``'s selectors. Returns None when the source is
    healthy (its current ``item`` selector still extracts rows from the live page).
    Otherwise proposes new selectors, validates them against the fetched HTML, and —
    when ``apply`` and validation passed — writes them to ``sources.toml`` and returns a
    ``HealResult`` describing the change (or a rejected proposal when validation
    failed).

    Raises:
        FetchError: the listing could not be fetched (propagated).
        HealError: the LLM proposal could not be obtained or parsed.
    """
    html = _fetch_listing(source, gate, session)
    if extract_items(html, source):
        return None   # still healthy; nothing to repair
    old = _selectors_of(source)
    proposed = propose_selectors(html, source, provider=provider, model=model, api_key=api_key)
    candidate = replace(source, item=proposed.get("item"), title=proposed.get("title"),
                        link=proposed.get("link"), date=proposed.get("date") or None)
    if not _validates(html, candidate):
        return HealResult(
            source_name=source.name, old=old, new=proposed, applied=False,
            note=f"proposed selectors for {source.name!r} did not extract; not applied")
    changes = {k: v for k, v in proposed.items() if k in _SELECTOR_KEYS and v}
    if apply:
        update_selectors(source.name, changes, path)
    diff = ", ".join(f"{k}: {old.get(k, '-')!r} -> {v!r}" for k, v in changes.items())
    return HealResult(source_name=source.name, old=old, new=changes, applied=apply,
                      note=f"repaired {source.name!r} selectors ({diff})")


def heal_empty_sources(
    sources: tuple[Source, ...], *, gate: RobotsGate, state: State,
    session: requests.Session | None = None,
    provider: str = DEFAULT_PROVIDER, model: str | None = None,
) -> tuple[str, ...]:
    """Heal each crawl source that has hit the empty-poll threshold; return the notes
    for the digest/log. A heal failure for one source is reported but does not abort the
    run, and a source's empty-poll counter is cleared once its repair is applied."""
    notes: list[str] = []
    for source in sources:
        if not needs_heal(source, state):
            continue
        try:
            result = heal_source(source, gate=gate, session=session, apply=True,
                                 provider=provider, model=model)
        except NewswatchError as err:
            notes.append(f"heal of {source.name!r} failed: {err}")
            continue
        if result is not None:
            notes.append(result.note)
            if result.applied:
                state.clear_empty(source.name)
    return tuple(notes)


def propose_selectors(
    html: str, source: Source, *, provider: str = DEFAULT_PROVIDER,
    model: str | None = None, api_key: str | None = None,
) -> dict[str, str]:
    """Ask an LLM for fresh CSS selectors for ``html``. Returns a map with item/title/
    link/date keys.

    Raises:
        HealError: the call failed or the reply was not the expected JSON object.
    """
    with make_llm_client(provider, model=model, api_key=api_key,
                        max_tokens=_MAX_TOKENS, action="healing") as client:
        try:
            reply = client.complete(_truncate(html), system=_SYSTEM).strip()
        except ThinchatError as err:
            raise HealError(
                f"selector proposal failed: {scrub_secrets(str(err))}"
            ) from scrub_exception(err)
    return _parse_selectors(reply)


def _validates(html: str, candidate: Source) -> bool:
    """Whether ``candidate``'s selectors extract at least ``_MIN_VALID_ROWS`` rows with
    non-empty title and link from ``html``."""
    if not (candidate.item and candidate.title and candidate.link):
        return False
    items = extract_items(html, candidate)
    good = [it for it in items if it.title and it.link]
    return len(good) >= _MIN_VALID_ROWS


def _selectors_of(source: Source) -> dict[str, str]:
    return {k: getattr(source, k) for k in _SELECTOR_KEYS if getattr(source, k)}


def _parse_selectors(reply: str) -> dict[str, str]:
    text = reply
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as err:
        raise HealError(f"LLM did not return selector JSON: {reply[:120]!r}") from err
    if not isinstance(parsed, dict):
        raise HealError("LLM selector reply was not a JSON object")
    return {k: str(parsed[k]) for k in _SELECTOR_KEYS if isinstance(parsed.get(k), str)}


def _truncate(html: str, limit: int = 12000) -> str:
    """Cap the HTML handed to the LLM — a listing's structure is near the top, and a
    smaller prompt is cheaper and within context."""
    return html if len(html) <= limit else html[:limit]


def _fetch_listing(source: Source, gate: RobotsGate | None, session: requests.Session | None) -> str:
    """Fetch the listing page (robots-gated). Seam for tests, which stub it and so may
    pass gate=None; the live path always has a gate."""
    if gate is None:
        raise HealError(f"cannot heal {source.name!r}: a robots gate is required")
    return get(source.url, gate, session=session)
