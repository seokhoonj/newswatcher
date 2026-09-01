"""The robots.txt gate every newswatcher HTTP fetch passes through.

A path a site's robots.txt disallows for our User-Agent is never requested — feed,
listing crawl, and article body alike. robots.txt is fetched once per host and
cached for the run. ``throttle`` paces consecutive fetches to a host by its requested
``Crawl-delay``, so the gate enforces both what may be fetched and how fast. Built on
the stdlib ``urllib.robotparser`` (no dependency); the robots.txt fetcher (and the
clock/sleep pacing uses) are injected so it is testable and reuses newswatcher's HTTP layer.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from urllib import robotparser
from urllib.parse import urlsplit, urlunsplit

__all__ = ["USER_AGENT", "RobotsGate"]

# An identifying User-Agent: robots rules match against it, and a site owner reading
# logs can see who we are. Sent on every request (see ``http``).
USER_AGENT = "newswatcher (+https://github.com/seokhoonj/newswatcher)"


class RobotsGate:
    """Per-host robots.txt cache answering ``can_fetch`` / ``crawl_delay``. Construct
    with the identifying ``user_agent`` and a ``fetch`` that returns a host's
    robots.txt text (or None when the host has no robots.txt — an absent robots.txt
    allows everything, the robots-spec default). A server error or unreachable host is
    the fetcher's concern: ``fetch`` returns disallow-all rules for those, not None."""

    def __init__(self, user_agent: str, fetch: Callable[[str], str | None], *,
                 sleep: Callable[[float], object] = time.sleep,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._user_agent = user_agent
        self._fetch = fetch
        self._parsers: dict[str, robotparser.RobotFileParser] = {}
        self._last_fetch: dict[str, float] = {}
        self._sleep = sleep
        self._clock = clock

    def can_fetch(self, url: str) -> bool:
        """Whether ``url`` may be fetched for our User-Agent under its host's robots.txt."""
        return self._parser_for(url).can_fetch(self._user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        """The Crawl-delay (seconds) the host requests for our User-Agent, or None."""
        delay = self._parser_for(url).crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None

    def throttle(self, url: str) -> None:
        """Sleep so consecutive fetches to ``url``'s host are at least its Crawl-delay
        apart, honoring the site's requested pace. The first fetch to a host never
        waits; a host with no Crawl-delay is not paced. ``http.get`` calls this before
        each request."""
        delay = self.crawl_delay(url)
        if not delay:
            return
        host = _host_key(url)
        last = self._last_fetch.get(host)
        if last is not None:
            wait = last + delay - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._last_fetch[host] = self._clock()

    def _parser_for(self, url: str) -> robotparser.RobotFileParser:
        host = _host_key(url)
        parser = self._parsers.get(host)
        if parser is None:
            parser = robotparser.RobotFileParser()
            text = self._fetch(_robots_url(url))
            if text is None:
                parser.parse([])   # no robots.txt -> allow everything
            else:
                parser.parse(text.splitlines())
            self._parsers[host] = parser
        return parser


def _host_key(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _robots_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
