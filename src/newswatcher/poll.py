"""One collect pass over every source: fetch, keep new-and-matching articles, fetch
each body, summarize, archive, and advance the watermark. The two collection means
(feed, crawl) are hidden behind ``_collect`` so the pipeline is one shape. A crawl
source that fetched fine but yielded no items increments its empty-poll counter (the
healer's trigger); a source whose fetch failed is skipped with a reason, not fatal --
one bad source must not stop the rest."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from newswatcher.body import fetch_body
from newswatcher.crawl import crawl_items
from newswatcher.errors import ArchiveError, NewswatcherError
from newswatcher.feed import FeedItem, fetch_feed
from newswatcher.match import assign_topics
from newswatcher.robots import RobotsGate
from newswatcher.sources import Source
from newswatcher.state import State
from newswatcher.store import Article, BodyStore, FileStore
from newswatcher.summarize import Summary, summarize_article
from newswatcher.topics import Topic

if TYPE_CHECKING:
    import requests

__all__ = ["PollReport", "poll_sources"]

Summarizer = Callable[[FeedItem, str], Summary]


@dataclass(frozen=True, slots=True, kw_only=True)
class PollReport:
    """What one poll produced: the ``collected`` new articles (in collection order), the
    ``empty_crawl_sources`` whose selector matched nothing, ``skipped`` as ``(name, reason)``
    pairs for items that were DROPPED -- a source whose fetch failed (name = source) or a
    single article whose summary or archive failed (name = article link) -- and
    ``body_failures`` as ``(link, reason)`` pairs where opt-in body capture failed -- a
    body failure never itself drops the article, though that article may still be dropped
    by a later summary/archive failure (then its link also appears in ``skipped``)."""

    collected:           tuple[Article, ...]
    empty_crawl_sources: tuple[str, ...]
    skipped:             tuple[tuple[str, str], ...]
    body_failures:       tuple[tuple[str, str], ...] = ()


def poll_sources(
    sources: tuple[Source, ...], topics: tuple[Topic, ...], *,
    gate: RobotsGate, state: State, store: FileStore | None,
    body_store: BodyStore | None = None,
    session: requests.Session | None = None, summarize: Summarizer = summarize_article,
) -> PollReport:
    """Run the pipeline once over ``sources``. Persists each collected article to
    ``store`` (when given) and advances ``state`` in place; the caller writes state and
    mails the digest. When ``body_store`` is given, each fetched body is also captured to
    it (opt-in raw-text keeping, separate from the article archive). ``summarize`` is
    injectable for tests. Does not raise for a source or article failure -- those are
    recorded in the report's ``skipped`` and the pass continues -- so a caller need not
    guard it against a single bad source."""
    collected: list[Article] = []
    empty: list[str] = []
    skipped: list[tuple[str, str]] = []
    body_failures: list[tuple[str, str]] = []
    for source in sources:
        try:
            items = _collect(source, gate, session)
        except NewswatcherError as err:
            skipped.append((source.name, str(err)))
            continue
        if not items:
            if source.kind == "crawl":
                state.note_empty(source.name)
                empty.append(source.name)
            continue
        if source.kind == "crawl":
            state.clear_empty(source.name)
        for article in _articles_from(source, items, topics, gate, state, store,
                                      body_store, session, summarize, skipped, body_failures):
            collected.append(article)
    return PollReport(collected=tuple(collected), empty_crawl_sources=tuple(empty),
                      skipped=tuple(skipped), body_failures=tuple(body_failures))


def _articles_from(
    source: Source, items: tuple[FeedItem, ...], topics: tuple[Topic, ...],
    gate: RobotsGate, state: State, store: FileStore | None, body_store: BodyStore | None,
    session: requests.Session | None, summarize: Summarizer, skipped: list[tuple[str, str]],
    body_failures: list[tuple[str, str]],
) -> Iterator[Article]:
    for item in items:
        if not state.is_new(source.name, item):
            continue
        tagged = assign_topics(item, source, topics)
        if tagged is None:
            state.mark_seen(source.name, item)   # advance past a non-match; never revisit
            continue
        body = _fetch_body(tagged, source, gate, session)
        # Capture the freshest body before summarizing, so it is kept even if the summary
        # is deferred (e.g. rate-limited). Best-effort: a body-store I/O failure is noted
        # but must not drop the article -- the summary is the archive's primary content.
        if body_store is not None and body:
            _store_body(body_store, tagged, body, body_failures)
        try:
            summary = summarize(tagged, body)
            article = Article(
                guid=tagged.guid, title=tagged.title, link=tagged.link,
                source_name=source.name, published=tagged.published, topics=tagged.topics,
                summary=summary.text, summary_model=summary.model,
            )
            if store is not None:
                store.save(article)
        except NewswatcherError as err:
            # A summary or archive failure drops this one article, not the poll (the
            # module invariant: one bad source must not stop the rest). Leave it
            # unmarked so a transient outage retries it on the next poll.
            skipped.append((tagged.link, str(err)))
            continue
        state.mark_seen(source.name, item)
        yield article


def _collect(source: Source, gate: RobotsGate, session: requests.Session | None) -> tuple[FeedItem, ...]:
    """Collect a source's current items by its kind. Seam for tests to stub the network."""
    if source.kind == "crawl":
        return crawl_items(source, gate, session=session)
    return fetch_feed(source, gate, session=session)


def _fetch_body(item: FeedItem, source: Source, gate: RobotsGate, session: requests.Session | None) -> str:
    """Fetch an article body, degrading to "" on any fetch failure -- a body problem
    must not drop the article (the summary falls back to the feed text). Seam for tests."""
    try:
        return fetch_body(item, source, gate, session=session)
    except NewswatcherError:
        return ""


def _store_body(body_store: BodyStore, item: FeedItem, body: str,
                body_failures: list[tuple[str, str]]) -> None:
    """Capture ``body`` to ``body_store``, best-effort: a failure is recorded in
    ``body_failures`` but does not by itself drop the article (body capture is secondary
    to the summary; the later summary/archive step decides whether it is collected)."""
    try:
        body_store.save(item.guid, body)
    except ArchiveError as err:
        body_failures.append((item.link, str(err)))
