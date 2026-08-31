"""The RSS/Atom source adapter: fetch a feed (robots-gated) and parse it into
``FeedItem``s. feedparser absorbs the RSS-vs-Atom and date-format variety so the
rest of the pipeline sees one shape. A crawl source produces the same ``FeedItem``
(see ``crawl``), so matching, body fetch, summary, and store are shared."""

from __future__ import annotations

import calendar
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING

import feedparser

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


# The dotted/slash numeric date stamps Korean news sites commonly render (feedparser
# parsed these; the stdlib parsers below do not, so recover them explicitly). Locale-
# independent -- all-numeric, no month names or AM/PM.
_NUMERIC_FORMATS = (
    "%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y.%m.%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
)


def normalize_date(text: str) -> str:
    """Parse a date string to the canonical ISO-8601 UTC form, or "" when it is empty or
    unrecognized. Accepts ISO-8601/W3CDTF, RFC 822 (as an RSS ``pubDate`` spells it), and
    the dotted/slash numeric stamps (``2026.08.15``, ``2026/08/15 09:00``) common on
    Korean news sites. Shared so a crawl source's raw date text normalizes to the same
    form ``_published`` produces for a feed entry. Parsed with the stdlib (``datetime`` +
    ``email.utils``) rather than a feed library's private helper, so the package's import
    surface stays stable."""
    text = text.strip()
    if not text:
        return ""
    moment = _parse_datetime(text)
    if moment is None:
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_datetime(text: str) -> datetime | None:
    """``text`` as a ``datetime`` if it is ISO-8601/W3CDTF, RFC 822, or a dotted/slash
    numeric stamp, else None."""
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text)
    except (ValueError, TypeError):
        pass
    for fmt in _NUMERIC_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def _published(entry: Mapping[str, object]) -> str:
    """An entry's published time as ISO-8601 UTC, or "" when absent. feedparser exposes a
    parsed ``published_parsed`` (a UTC ``time.struct_time``) when it could read any of the
    date fields; we format that one canonical form."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    return _iso8601(struct if isinstance(struct, time.struct_time) else None)


def _iso8601(struct: time.struct_time | None) -> str:
    """Format a UTC ``time.struct_time`` as ``YYYY-MM-DDTHH:MM:SSZ``; "" when None."""
    if not struct:
        return ""
    return datetime.fromtimestamp(calendar.timegm(struct), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
