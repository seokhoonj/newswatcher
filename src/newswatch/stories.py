"""Collapse near-duplicate articles that cover the same story.

Several outlets carrying one event each produce a distinct link -- and so a distinct
archive entry -- but a reader wants one line per real-world story, not one per outlet.
``group_stories`` folds a poll's collected articles into ``Story`` groups by title
similarity, so the digest shows a lead article with the others noted under it.

This is a presentation step over already-collected, already-archived articles: it never
drops or rewrites what the archive keeps -- every article, lead and duplicate alike, is
still stored on its own. Only the digest view collapses.

Similarity is character-bigram Jaccard over the normalized title -- language-agnostic
(the feeds are Korean and English), deterministic, and dependency-free. It catches the
near-identical headlines duplicates actually share: "코스피 3000 돌파" and
"코스피, 3000선 돌파" overlap on almost every bigram, where word-token overlap would miss
on the particle and the comma. It is lexical, not semantic -- the same event under two
entirely different headlines is not a duplicate here, by design."""

from __future__ import annotations

import re
from dataclasses import dataclass

from newswatch.store import Article

__all__ = ["Story", "group_stories", "title_similarity"]

# char-bigram Jaccard: near-identical headlines run high (0.7+), merely-related ones low
# (<0.3), so 0.5 separates them. Provisional until tuned against real feeds; exposed as a
# keyword on group_stories so tuning needs no code change.
_DEFAULT_THRESHOLD = 0.5

# Below this a title yields too few bigrams to score stably (a one- or two-character
# headline), so those compare by exact normalized equality instead of Jaccard.
_MIN_SHINGLES = 2


@dataclass(frozen=True, slots=True, kw_only=True)
class Story:
    """One real-world story and the articles that reported it. ``lead`` is the article the
    digest shows -- the first collected of the group; ``duplicates`` are the near-identical
    articles folded under it (empty for a story only one outlet ran). Every article, lead
    and duplicate alike, is still archived on its own -- a Story is a view, not a merge."""

    lead:       Article
    duplicates: tuple[Article, ...] = ()

    @property
    def also_reported_by(self) -> tuple[str, ...]:
        """The duplicates' source names, in first-seen order without repeats -- what the
        digest lists under the lead as also covering the story."""
        seen: dict[str, None] = {}
        for article in self.duplicates:
            seen.setdefault(article.source_name, None)
        return tuple(seen)


def group_stories(articles: tuple[Article, ...], *,
                  threshold: float = _DEFAULT_THRESHOLD) -> tuple[Story, ...]:
    """Fold ``articles`` into stories by title similarity, preserving the order in which
    each story's lead first appears. Greedy first-fit: each article joins the first
    earlier lead it is similar enough to (``>= threshold``), or starts a new story. That
    avoids the transitive chaining a full clustering pass would introduce -- A~B and B~C
    merging A and C even when A and C are unalike -- and is deterministic in collection
    order (the order the poll fetched sources and their items)."""
    leads: list[Article] = []
    members: list[list[Article]] = []
    for article in articles:
        for index, lead in enumerate(leads):
            if title_similarity(article.title, lead.title) >= threshold:
                members[index].append(article)
                break
        else:
            leads.append(article)
            members.append([])
    return tuple(Story(lead=lead, duplicates=tuple(group))
                 for lead, group in zip(leads, members, strict=True))


def title_similarity(a: str, b: str) -> float:
    """How alike two titles are, from 0.0 to 1.0: the Jaccard overlap of their character
    bigrams after normalization. 1.0 is identical text (near-identical headlines score
    high, unrelated ones low). A title too short to yield bigrams compares by exact
    normalized equality (1.0 or 0.0) instead, so two one-word headlines do not merge on a
    single shared character; two empty titles are never similar."""
    shingles_a = _shingles(a)
    shingles_b = _shingles(b)
    if len(shingles_a) < _MIN_SHINGLES or len(shingles_b) < _MIN_SHINGLES:
        normalized = _normalize(a)
        return 1.0 if normalized and normalized == _normalize(b) else 0.0
    return len(shingles_a & shingles_b) / len(shingles_a | shingles_b)


def _shingles(title: str) -> frozenset[str]:
    """The set of character bigrams of the normalized, space-stripped title, so two
    headlines differing only in spacing or punctuation share their shingles. Empty when
    the compacted title has fewer than two characters."""
    compact = _normalize(title).replace(" ", "")
    return frozenset(compact[index:index + 2] for index in range(len(compact) - 1))


def _normalize(title: str) -> str:
    """Lowercase, with every run of non-word characters collapsed to a single space and
    the ends stripped -- so quotes, commas, and spacing differences do not split an
    otherwise-identical headline. ``\\w`` keeps letters (Korean included) and digits;
    only separators go."""
    return re.sub(r"\W+", " ", title.lower()).strip()
