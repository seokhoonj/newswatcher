"""The RSS/Atom source adapter: fetch a feed (robots-gated) and parse it into
``FeedItem``s. feedparser absorbs the RSS-vs-Atom and date-format variety so the
rest of the pipeline sees one shape. A crawl source produces the same ``FeedItem``
(see ``crawl``), so matching, body fetch, summary, and store are shared."""

from __future__ import annotations

import calendar
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import feedparser
from feedparser.datetimes import _parse_date

from newswatch.http import get
from newswatch.robots import RobotsGate
from newswatch.sources import Source

if TYPE_CHECKING:
    import requests

__all__ = ["FeedItem", "parse_feed", "fetch_feed", "normalize_date"]


@dataclass(frozen=True, slots=True)
class FeedItem:
    """One article as collected from a source, before topic matching. ``guid`` is the
    item's stable id (its RSS guid, or its link when none), used to dedup against the
    watermark. ``published`` is ISO-8601 UTC (``YYYY-MM-DDTHH:MM:SSZ``) or "" when the
    source gave no date. ``summary`` is the feed-provided description (may be empty).
    ``topics`` is filled by matching (empty as collected)."""

    title:       str
    link:        str
    guid:        str
    summary:     str = ""
    published:   str = ""
    source_name: str = ""
    topics:      tuple[str, ...] = field(default=(), kw_only=True)


def fetch_feed(source: Source, gate: RobotsGate, *,
               session: requests.Session | None = None) -> tuple[FeedItem, ...]:
    """Fetch and parse ``source``'s RSS feed into items.

    Raises:
        FetchError: robots disallows the feed URL or the fetch failed (propagated
            from ``http.get``).
    """
    return parse_feed(get(source.url, gate, session=session), source.name)


def parse_feed(text: str, source_name: str) -> tuple[FeedItem, ...]:
    """Parse feed ``text`` into items. Never raises on malformed feeds -- feedparser
    is tolerant and simply yields the entries it can read; an entry missing a link is
    skipped (nothing to fetch or dedup on)."""
    parsed = feedparser.parse(text)
    items = []
    for entry in parsed.entries:
        link = (entry.get("link") or "").strip()
        if not link:
            continue
        guid = (entry.get("id") or link).strip()
        items.append(FeedItem(
            title=(entry.get("title") or "").strip(),
            link=link,
            guid=guid,
            summary=(entry.get("summary") or "").strip(),
            published=_published(entry),
            source_name=source_name,
        ))
    return tuple(items)


def normalize_date(text: str) -> str:
    """Parse an arbitrary date string (RSS, W3CDTF/ISO, RFC822, ...) to the canonical
    ISO-8601 UTC form, or "" when it is empty or feedparser cannot parse it. Shared so
    a crawl source's raw date text normalizes to the same form ``_published`` produces
    for a feed entry."""
    return _iso8601(_parse_date(text)) if text else ""


def _published(entry: object) -> str:
    """An entry's published time as ISO-8601 UTC, or "" when absent. feedparser
    exposes a parsed ``published_parsed`` (a UTC ``time.struct_time``) when it could
    read any of the date fields; we format that one canonical form."""
    struct = getattr(entry, "get", lambda *_: None)("published_parsed") \
        or getattr(entry, "get", lambda *_: None)("updated_parsed")
    return _iso8601(struct)


def _iso8601(struct: time.struct_time | None) -> str:
    """Format a UTC ``time.struct_time`` as ``YYYY-MM-DDTHH:MM:SSZ``; "" when None."""
    if not struct:
        return ""
    return datetime.fromtimestamp(calendar.timegm(struct), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
