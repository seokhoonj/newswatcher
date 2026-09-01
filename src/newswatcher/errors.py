"""Domain exception hierarchy for newswatcher.

Every error newswatcher raises on purpose derives from ``NewswatcherError``, so a
caller can handle this package's failures with one ``except`` without catching
unrelated bugs.
"""

from __future__ import annotations

__all__ = [
    "NewswatcherError",
    "ConfigError",
    "SourceError",
    "TopicError",
    "FetchError",
    "ArchiveError",
    "LLMError",
    "DigestError",
    "ScheduleError",
    "HealError",
]


class NewswatcherError(Exception):
    """Base for every error newswatcher raises deliberately."""


class ConfigError(NewswatcherError):
    """A newswatcher config file (settings, topics, sources, or credentials) is missing or
    malformed."""


class SourceError(NewswatcherError):
    """A source entry is invalid: missing url, unknown kind, or a crawl source
    lacking the selectors its kind requires."""


class TopicError(NewswatcherError):
    """A topic entry is invalid: missing name, or includes/excludes of the wrong shape."""


class FetchError(NewswatcherError):
    """An HTTP fetch (feed, listing page, or article body) failed, or robots.txt
    disallowed the URL. Its message carries the URL and the underlying cause."""


class ArchiveError(NewswatcherError):
    """The article archive could not be read or written (an I/O failure), kept
    distinct from a corrupt file, which is treated as absent rather than raised."""


class LLMError(NewswatcherError):
    """An LLM feature (summary, heal) failed: no API key, unknown provider, an API
    error, or a reply of the wrong shape. Its message carries the underlying cause."""


class DigestError(NewswatcherError):
    """A digest could not be delivered: a delivery package (``mailmail`` for email,
    ``pushpush`` for chat) is missing, or a destination refused or failed the send. Its
    message carries the underlying cause."""


class ScheduleError(NewswatcherError):
    """The OS scheduler could not be queried or changed."""


class HealError(NewswatcherError):
    """A selector-repair pass failed to produce validated selectors."""
