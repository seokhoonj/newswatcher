"""The crawl source adapter: fetch a listing page (robots-gated) and pull articles
out of its HTML with the per-source CSS selectors. Produces the same ``FeedItem`` an
RSS feed does, so everything downstream is shared. Selectors are the source's own
(``item`` / ``title`` / ``link`` / ``date``); ``link`` and ``date`` may read an
attribute via the ``css@attr`` form. Used only where a site has no feed and its
robots.txt permits the listing page; when the ``item`` selector stops matching, the
healer (see ``heal``) repairs it."""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from newswatch.feed import FeedItem, normalize_date
from newswatch.http import get
from newswatch.robots import RobotsGate
from newswatch.sources import Source

__all__ = ["extract_items", "crawl_items", "parse_selector"]


def crawl_items(source: Source, gate: RobotsGate, *, session: object | None = None
                ) -> tuple[FeedItem, ...]:
    """Fetch ``source``'s listing page and extract its article items.

    Raises:
        FetchError: robots disallows the listing URL or the fetch failed (propagated
            from ``http.get``).
    """
    import requests

    html = get(source.url, gate, session=session if isinstance(session, requests.Session) else None)
    return extract_items(html, source)


def extract_items(html: str, source: Source) -> tuple[FeedItem, ...]:
    """Extract items from listing ``html`` using ``source``'s selectors. A row whose
    link resolves empty is skipped (nothing to fetch or dedup on). Relative links are
    resolved against the source URL. Never raises on selector misses — a zero-row
    result is the healer's trigger, not an error here."""
    soup = BeautifulSoup(html, "lxml")
    assert source.item and source.title and source.link  # guaranteed by Source validation
    items = []
    for row in soup.select(source.item):
        link = _select_value(row, source.link, base=source.url)
        if not link:
            continue
        title = _select_value(row, source.title) or ""
        raw_date = _select_value(row, source.date) if source.date else ""
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


def _select_value(row: object, selector: str, *, base: str | None = None) -> str:
    """The text (or attribute) of the first element under ``row`` matching ``selector``,
    "" when none matches. With ``base`` an attribute value is joined onto it (relative
    link -> absolute)."""
    css, attr = parse_selector(selector)
    found = row.select_one(css)  # type: ignore[attr-defined]
    if found is None:
        return ""
    if attr is not None:
        value = (found.get(attr) or "").strip()
        return urljoin(base, value) if base and value else value
    return str(found.get_text(strip=True))
