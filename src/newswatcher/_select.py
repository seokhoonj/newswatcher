"""Run a CSS selector, turning a malformed-selector error into a domain ``SourceError``.

soupsieve raises two unrelated classes for a bad selector: ``SelectorSyntaxError`` for a
syntax error (``>>bad``, ``a[``), and a bare ``NotImplementedError`` for an unsupported
pseudo-element (``a::attr(href)``, ``a::text`` -- the Scrapy idiom an LLM healer readily
emits). Both are caught here, in one place used by both the crawl adapter and the body
extractor, so one bad selector -- hand-typed in ``sources.toml`` or proposed by the healer
-- skips its source (the poll catches ``SourceError`` per source) instead of aborting the
whole pass with a raw error the pipeline does not expect."""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from soupsieve import SelectorSyntaxError

from newswatcher.errors import SourceError

__all__ = ["select_all", "select_one"]


def select_all(node: Tag | BeautifulSoup, selector: str, source_name: str) -> list[Tag]:
    """``node.select(selector)`` with a malformed selector reported as ``SourceError``."""
    try:
        return node.select(selector)
    except (SelectorSyntaxError, NotImplementedError) as err:
        raise SourceError(
            f"source {source_name!r}: invalid CSS selector {selector!r}: {err}") from err


def select_one(node: Tag | BeautifulSoup, selector: str, source_name: str) -> Tag | None:
    """``node.select_one(selector)`` with a malformed selector reported as ``SourceError``."""
    try:
        return node.select_one(selector)
    except (SelectorSyntaxError, NotImplementedError) as err:
        raise SourceError(
            f"source {source_name!r}: invalid CSS selector {selector!r}: {err}") from err
