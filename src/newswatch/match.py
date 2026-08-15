"""Decide which topics an article belongs to.

A topic keeps an article whose title or summary contains any of its ``includes``
words (case-insensitive; empty includes = keep all), unless it also contains an
``excludes`` word. ASCII keywords match whole words, while Korean keywords also
match inside compounds. A source is tested only against the topics it subscribes
to; a ``keep_all`` source skips the keyword test and is tagged with all its
subscribed topics (a trade paper whose whole feed is on-topic)."""

from __future__ import annotations

import re
from dataclasses import replace

from newswatch.feed import FeedItem
from newswatch.sources import Source
from newswatch.topics import Topic

__all__ = ["matches_topic", "topics_for", "assign_topics"]


def matches_topic(item: FeedItem, topic: Topic) -> bool:
    """Whether ``item`` matches ``topic``: any include word present in its title or
    summary (empty includes = match), and no exclude word present."""
    haystack = f"{item.title}\n{item.summary}".lower()
    if any(_contains_word(haystack, word) for word in topic.excludes):
        return False
    if not topic.includes:
        return True
    return any(_contains_word(haystack, word) for word in topic.includes)


def topics_for(item: FeedItem, source: Source, topics: tuple[Topic, ...]) -> tuple[str, ...]:
    """The names of ``source``'s subscribed topics that ``item`` is tagged with. For a
    ``keep_all`` source that is every subscribed topic; otherwise only those whose
    keyword filter the item passes. Order follows the source's ``topics`` list."""
    by_name = {topic.name: topic for topic in topics}
    tagged = []
    for name in source.topics:
        topic = by_name.get(name)
        if topic is None:
            continue   # a source naming an undefined topic simply contributes no tag
        if source.keep_all or matches_topic(item, topic):
            tagged.append(name)
    return tuple(tagged)


def assign_topics(item: FeedItem, source: Source, topics: tuple[Topic, ...]) -> FeedItem | None:
    """Return ``item`` with its matched topic names set, or None when it matched no
    subscribed topic (so the caller drops it)."""
    tags = topics_for(item, source, topics)
    if not tags:
        return None
    return replace(item, topics=tags)


def _contains_word(haystack_lower: str, word: str) -> bool:
    """Whether ``word`` appears in the already-lowercased haystack.

    Korean keywords match compounds such as ``보험료`` and ``손보사``; other
    keywords use regular-expression word boundaries.
    """
    if not word:
        return False
    word_lower = word.lower()
    if any("가" <= character <= "힣" for character in word_lower):
        return word_lower in haystack_lower
    return re.search(rf"\b{re.escape(word_lower)}\b", haystack_lower) is not None
