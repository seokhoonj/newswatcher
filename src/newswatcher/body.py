"""Fetch an article page and extract its main text — the raw material an LLM summary
is written from. The body is transient: it is never stored in the archive nor placed
in the outbound email (which carry only our summary plus the link). Extraction uses
the source's ``body_selector`` when it defines one, else the generic extractor
(trafilatura)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import trafilatura
from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError

from newswatcher.errors import SourceError
from newswatcher.feed import FeedItem
from newswatcher.http import get
from newswatcher.robots import RobotsGate
from newswatcher.sources import Source

if TYPE_CHECKING:
    import requests

__all__ = ["extract_body", "fetch_body"]


def fetch_body(item: FeedItem, source: Source, gate: RobotsGate, *,
               session: requests.Session | None = None) -> str:
    """Fetch ``item``'s article page (robots-gated) and extract its body text, or ""
    when nothing could be extracted.

    Raises:
        FetchError: robots disallows the article URL or the fetch failed (propagated
            from ``http.get``).
    """
    return extract_body(get(item.link, gate, session=session), source)


def extract_body(html: str, source: Source) -> str:
    """Extract the article body from ``html``. With ``source.body_selector`` set, the
    text of the first matching node; otherwise trafilatura's main-content extraction.
    Returns "" when neither yields text (a summary step then falls back to the feed
    title/summary)."""
    if source.body_selector:
        try:
            node = BeautifulSoup(html, "lxml").select_one(source.body_selector)
        except SelectorSyntaxError as err:
            raise SourceError(
                f"source {source.name!r}: invalid body_selector "
                f"{source.body_selector!r}: {err}") from err
        return node.get_text(" ", strip=True) if node is not None else ""
    extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
    return (extracted or "").strip()
