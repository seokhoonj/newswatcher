"""Classify an article's origin region for the digest's domestic/overseas split.

A source may declare its region explicitly -- ``kr`` (domestic) or ``intl`` (overseas) --
and when it does not, the region is inferred from the article's own title: Korean text
reads as domestic, everything else as overseas. Inference is a sensible default, not a
rule. An English-language Korean outlet (e.g. an English-titled domestic paper) carries no
Hangul in its titles, so it should be tagged ``kr`` explicitly rather than left to the
guess -- title *inference*, finding no Hangul, resolves to ``intl``. ``DEFAULT_REGION`` is
a separate fallback: where an *unknown region code* (a stored value that is neither ``kr``
nor ``intl``) lands, kept domestic because that is the primary audience."""

from __future__ import annotations

__all__ = ["REGIONS", "DEFAULT_REGION", "infer_region", "resolve_region", "region_label"]

REGIONS = ("kr", "intl")
DEFAULT_REGION = "kr"

_LABELS = {"kr": "국내", "intl": "해외"}


def infer_region(title: str) -> str:
    """``"kr"`` when ``title`` contains any Hangul syllable, else ``"intl"`` -- a language
    proxy for origin, since domestic outlets title in Korean and overseas ones do not."""
    return "kr" if any("가" <= ch <= "힣" for ch in title) else "intl"


def resolve_region(source_region: str, title: str) -> str:
    """The region to tag an article with: the source's explicit ``kr``/``intl`` when it set
    one, else inferred from ``title``. An unrecognized source value (a typo, an old value)
    falls back to inference rather than mislabeling every article from that source."""
    if source_region in REGIONS:
        return source_region
    return infer_region(title)


def region_label(region: str) -> str:
    """The Korean display label for a region code (``국내`` / ``해외``); the raw code for an
    unknown value, so a future region still renders something rather than blank."""
    return _LABELS.get(region, region)
