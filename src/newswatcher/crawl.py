"""The crawl source adapter: fetch a listing page (robots-gated) and pull articles
out of its HTML with the per-source CSS selectors. Produces the same ``FeedItem`` an
RSS feed does, so everything downstream is shared. Selectors are the source's own
(``item`` / ``title`` / ``link`` / ``date``); ``link`` and ``date`` may read an
attribute via the ``css@attr`` form. Used only where a site has no feed and its
robots.txt permits the listing page; when the ``item`` selector stops matching, the
healer (see ``heal``) repairs it."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from newswatcher._select import select_all, select_one
from newswatcher.errors import SourceError
from newswatcher.feed import FeedItem, normalize_date
from newswatcher.http import get
from newswatcher.robots import RobotsGate
from newswatcher.sources import Source

if TYPE_CHECKING:
    import requests

__all__ = ["extract_items", "crawl_items", "parse_selector"]


def crawl_items(source: Source, gate: RobotsGate, *,
                session: requests.Session | None = None) -> tuple[FeedItem, ...]:
    """Fetch ``source``'s listing page and extract its article items.

    Raises:
        FetchError: robots disallows the listing URL or the fetch failed (propagated
            from ``http.get``).
    """
    return extract_items(get(source.url, gate, session=session), source)


def extract_items(html: str, source: Source) -> tuple[FeedItem, ...]:
    """Extract items from listing ``html`` using ``source``'s selectors. A row whose
    link resolves empty is skipped (nothing to fetch or dedup on). Relative links are
    resolved against the source URL. Never raises on selector misses — a zero-row
    result is the healer's trigger, not an error here."""
    if not (source.item and source.title and source.link):
        # add_source/_source_from validate this, but Source() itself does not, and an
        # assert would vanish under python -O -- raise the domain error unconditionally.
        raise SourceError(
            f"crawl source {source.name!r} is missing its item/title/link selectors")
    soup = BeautifulSoup(html, "lxml")
    items = []
    for row in select_all(soup, source.item, source.name):
        link = _select_value(row, source.link, source.name, base=source.url)
        if not link:
            continue
        title = _select_value(row, source.title, source.name) or ""
        raw_date = _select_value(row, source.date, source.name) if source.date else ""
        items.append(FeedItem(
            title=title,
            link=link,
            guid=link,   # a listing rarely exposes a stable id; the link is the dedup key
            summary="",
            published=normalize_date(raw_date),   # to ISO-8601, or "" when unparseable
            source_name=source.name,
        ))
    return tuple(items)


def parse_selector(selector: str) -> tuple[str, str | None]:
    """Split a ``css@attr`` selector into ``(css, attr)``; ``attr`` is None for a plain
    selector (read the element's text). Only the last ``@`` splits, so a CSS attribute
    selector like ``a[data-x]@href`` still works."""
    css, sep, attr = selector.rpartition("@")
    if not sep:
        return selector, None
    return css, attr


def _select_value(row: Tag, selector: str, source_name: str, *, base: str | None = None) -> str:
    """The text (or attribute) of the first element under ``row`` matching ``selector``,
    "" when none matches. With ``base`` an attribute value is joined onto it (relative
    link -> absolute)."""
    css, attr = parse_selector(selector)
    found = select_one(row, css, source_name)
    if found is None:
        return ""
    if attr is not None:
        raw = found.get(attr)
        if isinstance(raw, list):   # a multi-valued attribute (e.g. class); join it
            raw = " ".join(raw)
        value = (raw or "").strip()
        return urljoin(base, value) if base and value else value
    return found.get_text(strip=True)
