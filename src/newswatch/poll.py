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

from newswatch.article import fetch_body
from newswatch.crawl import crawl_items
from newswatch.errors import NewswatchError
from newswatch.feed import FeedItem, fetch_feed
from newswatch.match import assign_topics
from newswatch.robots import RobotsGate
from newswatch.sources import Source
from newswatch.state import State
from newswatch.store import Article, FileStore
from newswatch.summarize import Summary, summarize_article
from newswatch.topics import Topic

if TYPE_CHECKING:
    import requests

__all__ = ["PollReport", "poll_sources"]

Summarizer = Callable[[FeedItem, str], Summary]


@dataclass(frozen=True, slots=True, kw_only=True)
class PollReport:
    """What one poll produced: the ``collected`` new articles (in collection order),
    the ``empty_crawl_sources`` whose selector matched nothing, and ``skipped`` as
    ``(name, reason)`` pairs -- a source whose fetch failed (name = source), or a single
    article whose summary or archive failed (name = article link)."""

    collected:           tuple[Article, ...]
    empty_crawl_sources: tuple[str, ...]
    skipped:             tuple[tuple[str, str], ...]


def poll_sources(
    sources: tuple[Source, ...], topics: tuple[Topic, ...], *,
    gate: RobotsGate, state: State, store: FileStore | None,
    session: requests.Session | None = None, summarize: Summarizer = summarize_article,
) -> PollReport:
    """Run the pipeline once over ``sources``. Persists each collected article to
    ``store`` (when given) and advances ``state`` in place; the caller writes state and
    mails the digest. ``summarize`` is injectable for tests."""
    collected: list[Article] = []
    empty: list[str] = []
    skipped: list[tuple[str, str]] = []
    for source in sources:
        try:
            items = _collect(source, gate, session)
        except NewswatchError as err:
            skipped.append((source.name, str(err)))
            continue
        if not items:
            if source.kind == "crawl":
                state.note_empty(source.name)
                empty.append(source.name)
            continue
        if source.kind == "crawl":
            state.clear_empty(source.name)
        for article in _process(source, items, topics, gate, state, store,
                                session, summarize, skipped):
            collected.append(article)
    return PollReport(collected=tuple(collected), empty_crawl_sources=tuple(empty),
                      skipped=tuple(skipped))


def _process(
    source: Source, items: tuple[FeedItem, ...], topics: tuple[Topic, ...],
    gate: RobotsGate, state: State, store: FileStore | None,
    session: requests.Session | None, summarize: Summarizer, skipped: list[tuple[str, str]],
) -> Iterator[Article]:
    for item in items:
        if not state.is_new(source.name, item):
            continue
        tagged = assign_topics(item, source, topics)
        if tagged is None:
            state.mark_seen(source.name, item)   # advance past a non-match; never revisit
            continue
        body = _fetch_body(tagged, source, gate, session)
        try:
            summary = summarize(tagged, body)
            article = Article(
                guid=tagged.guid, title=tagged.title, link=tagged.link,
                source_name=source.name, published=tagged.published, topics=tagged.topics,
                summary=summary.text, summary_model=summary.model,
            )
            if store is not None:
                store.save(article)
        except NewswatchError as err:
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
    except NewswatchError:
        return ""
