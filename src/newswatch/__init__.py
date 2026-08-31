"""newswatch: watch news sources (RSS or robots-permitted crawl), match topics,
summarize with an LLM, and mail a digest."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("newswatch")
except PackageNotFoundError:   # not installed (e.g. run from a source tree)
    __version__ = "0.0.0+unknown"
