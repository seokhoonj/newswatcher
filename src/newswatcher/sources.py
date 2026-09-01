"""The set of news sources, read from ``sources.toml`` in ``config_dir()``.

A source yields a stream of articles by one of two means:

- ``kind = "rss"`` — ``url`` is an RSS/Atom feed (see ``feed``).
- ``kind = "crawl"`` — ``url`` is a listing page whose articles are pulled out with
  the CSS selectors ``item`` / ``title`` / ``link`` (and optional ``date``); used
  only where the site has no feed and its robots.txt permits fetching (see ``crawl``).

``topics`` names the topics this source is tested against and tagged with.
``keep_all`` skips the keyword filter for the source — every article is kept and
tagged with ``topics`` — which is how a trade paper (whole feed on-topic) is taken
in full while a general paper is keyword-filtered. ``body_selector`` optionally
overrides generic body extraction for this source's articles.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal, get_args

from newswatcher import _toml
from newswatcher._atomic import write_text_atomic
from newswatcher.config import config_dir
from newswatcher.errors import SourceError

__all__ = ["Source", "SourceKind", "sources_path", "load_sources", "add_source",
           "update_selectors"]

SourceKind = Literal["rss", "crawl"]
_KINDS: tuple[SourceKind, ...] = get_args(SourceKind)
# The crawl selector fields, in the order they render; item/title/link are required
# for a crawl source, date/body_selector are optional.
_SOURCE_SELECTOR_FIELDS = ("item", "title", "link", "date", "body_selector")
_REQUIRED_CRAWL = ("item", "title", "link")


@dataclass(frozen=True, slots=True)
class Source:
    """One news source and how to collect it. See the module docstring for field
    meaning. Everything past ``name`` is keyword-only so a positional call cannot
    silently swap the many optional fields."""

    name:          str
    kind:          SourceKind = field(default="rss", kw_only=True)
    url:           str = field(default="", kw_only=True)
    topics:        tuple[str, ...] = field(default=(), kw_only=True)
    keep_all:      bool = field(default=False, kw_only=True)
    item:          str | None = field(default=None, kw_only=True)
    title:         str | None = field(default=None, kw_only=True)
    link:          str | None = field(default=None, kw_only=True)
    date:          str | None = field(default=None, kw_only=True)
    body_selector: str | None = field(default=None, kw_only=True)


def sources_path() -> Path:
    """The sources file, ``sources.toml`` in ``config_dir()``.

    Raises:
        ConfigError: no config directory can be resolved (propagated from ``config_dir``)."""
    return config_dir() / "sources.toml"


def load_sources(path: Path | None = None) -> tuple[Source, ...]:
    """Read and validate the sources list; empty tuple when the file is absent.

    Raises:
        SourceError: the file is unreadable, an entry is missing name/url, names an
            unknown kind, or is a crawl source without its required selectors.
    """
    path = path or sources_path()
    if not path.exists():
        return ()
    return tuple(_source_from(entry, path)
                 for entry in _toml.read_table_array(path, "source", SourceError))


def add_source(source: Source, path: Path | None = None) -> bool:
    """Append ``source`` to ``sources.toml`` (creating it if absent); return whether
    it was added (False if the name already exists — idempotent).

    Raises:
        SourceError: the new source is invalid, or the file is malformed or unwritable.
    """
    path = path or sources_path()
    _validate(source)
    existing = load_sources(path) if path.exists() else ()
    if any(current.name == source.name for current in existing):
        return False
    write_text_atomic(path, _render((*existing, source)), SourceError)
    return True


def update_selectors(name: str, selectors: dict[str, str], path: Path | None = None) -> None:
    """Replace the given selector fields of source ``name`` in place, preserving all
    other fields and the rest of the file. Used by the healer to persist a repair.

    Raises:
        SourceError: no source named ``name`` exists, a key is not a selector field,
            or the file is malformed or unwritable.
    """
    path = path or sources_path()
    unknown = set(selectors) - set(_SOURCE_SELECTOR_FIELDS)
    if unknown:
        raise SourceError(f"not selector fields: {', '.join(sorted(unknown))}")
    sources = load_sources(path)
    if not any(s.name == name for s in sources):
        raise SourceError(f"no source named {name!r} to update")
    updated = tuple(
        # keys are validated above to be selector fields, all typed str | None, so the
        # str values are valid -- but mypy cannot see the guard, hence the narrow ignore.
        replace(s, **selectors) if s.name == name else s  # type: ignore[arg-type]
        for s in sources
    )
    write_text_atomic(path, _render(updated), SourceError)


def _source_from(entry: dict[str, object], path: Path) -> Source:
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SourceError(f"a [[source]] in {path} is missing 'name'")
    kind = entry.get("kind", "rss")
    if not isinstance(kind, str) or kind not in _KINDS:
        raise SourceError(f"source {name!r}: unknown kind {kind!r}; "
                          f"choose one of {', '.join(_KINDS)}")
    url = entry.get("url")
    if not isinstance(url, str) or not url.strip():
        raise SourceError(f"source {name!r} is missing 'url'")
    source = Source(
        name.strip(),
        kind=kind,
        url=url.strip(),
        topics=_str_tuple(entry.get("topics", ()), name),
        keep_all=_bool(entry.get("keep_all", False), name),
        item=_opt_str(entry.get("item")),
        title=_opt_str(entry.get("title")),
        link=_opt_str(entry.get("link")),
        date=_opt_str(entry.get("date")),
        body_selector=_opt_str(entry.get("body_selector")),
    )
    _validate(source)
    return source


def _validate(source: Source) -> None:
    if source.kind not in _KINDS:
        raise SourceError(f"source {source.name!r}: unknown kind {source.kind!r}; "
                          f"choose one of {', '.join(_KINDS)}")
    if source.kind == "crawl":
        missing = [f for f in _REQUIRED_CRAWL if getattr(source, f) is None]
        if missing:
            raise SourceError(f"crawl source {source.name!r} is missing selector(s): "
                              f"{', '.join(missing)}")


def _str_tuple(raw: object, name: object) -> tuple[str, ...]:
    if isinstance(raw, str):
        raw = [raw]
    elif not isinstance(raw, (list, tuple)):
        raise SourceError(f"source {name!r}: topics must be a string or a list")
    return tuple(str(word) for word in raw)


def _bool(raw: object, name: object) -> bool:
    if not isinstance(raw, bool):
        raise SourceError(f"source {name!r}: keep_all must be true or false, got {raw!r}")
    return raw


def _opt_str(raw: object) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def _render(sources: tuple[Source, ...]) -> str:
    blocks = []
    for s in sources:
        lines = [
            "[[source]]",
            f"name = {_toml.quote(s.name)}",
            f"kind = {_toml.quote(s.kind)}",
            f"url = {_toml.quote(s.url)}",
        ]
        if s.topics:
            lines.append(f"topics = {_toml.array(s.topics)}")
        if s.keep_all:
            lines.append("keep_all = true")
        for field_name in _SOURCE_SELECTOR_FIELDS:
            value = getattr(s, field_name)
            if value is not None:
                lines.append(f"{field_name} = {_toml.quote(value)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"
