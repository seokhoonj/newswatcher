"""Domain exception hierarchy for newswatch.

Every error newswatch raises on purpose derives from ``NewswatchError``, so a
caller can handle this package's failures with one ``except`` without catching
unrelated bugs.
"""

from __future__ import annotations

__all__ = [
    "NewswatchError",
    "ConfigError",
    "SourceError",
    "TopicError",
    "FetchError",
    "CorpusError",
    "LLMError",
    "NotifyError",
    "ScheduleError",
    "HealError",
]


class NewswatchError(Exception):
    """Base for every error newswatch raises deliberately."""


class ConfigError(NewswatchError):
    """A newswatch config file (settings, topics, or sources) is missing or malformed."""


class SourceError(NewswatchError):
    """A source entry is invalid: missing url, unknown kind, or a crawl source
    lacking the selectors its kind requires."""


class TopicError(NewswatchError):
    """A topic entry is invalid: missing name, or includes/excludes of the wrong shape."""


class FetchError(NewswatchError):
    """An HTTP fetch (feed, listing page, or article body) failed, or robots.txt
    disallowed the URL. Its message carries the URL and the underlying cause."""


class CorpusError(NewswatchError):
    """The article archive could not be read or written (an I/O failure), kept
    distinct from a corrupt file, which is treated as absent rather than raised."""


class LLMError(NewswatchError):
    """An LLM feature (summary, heal) failed: no API key, unknown provider, an API
    error, or a reply of the wrong shape. Its message carries the underlying cause."""


class NotifyError(NewswatchError):
    """A digest could not be mailed: the ``mailmail`` package is missing, or it
    refused or failed the send. Its message carries the underlying cause."""


class ScheduleError(NewswatchError):
    """The OS scheduler could not be queried or changed."""


class HealError(NewswatchError):
    """A selector-repair pass failed to produce validated selectors."""
