"""The robots.txt gate every newswatch HTTP fetch passes through.

A path a site's robots.txt disallows for our User-Agent is never requested — feed,
listing crawl, and article body alike. robots.txt is fetched once per host and
cached for the run. ``crawl_delay`` exposes the site's requested delay so the poll
can pace itself. Built on the stdlib ``urllib.robotparser`` (no dependency); the
robots.txt fetcher is injected so it is testable and reuses newswatch's HTTP layer.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib import robotparser
from urllib.parse import urlsplit, urlunsplit

__all__ = ["USER_AGENT", "RobotsGate", "default_gate"]

# An identifying User-Agent: robots rules match against it, and a site owner reading
# logs can see who we are. Sent on every request (see ``http``).
USER_AGENT = "newswatch (+https://github.com/seokhoonj/newswatch)"


class RobotsGate:
    """Per-host robots.txt cache answering ``can_fetch`` / ``crawl_delay``. Construct
    with the identifying ``user_agent`` and a ``fetch`` that returns a host's
    robots.txt text (or None when the host has none / it could not be fetched — an
    absent robots.txt allows everything, the robots-spec default)."""

    def __init__(self, user_agent: str, fetch: Callable[[str], str | None]) -> None:
        self._user_agent = user_agent
        self._fetch = fetch
        self._parsers: dict[str, robotparser.RobotFileParser] = {}

    def can_fetch(self, url: str) -> bool:
        """Whether ``url`` may be fetched for our User-Agent under its host's robots.txt."""
        return self._parser_for(url).can_fetch(self._user_agent, url)

    def crawl_delay(self, url: str) -> float | None:
        """The Crawl-delay (seconds) the host requests for our User-Agent, or None."""
        delay = self._parser_for(url).crawl_delay(self._user_agent)
        return float(delay) if delay is not None else None

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


def default_gate() -> RobotsGate:
    """A gate whose fetcher pulls robots.txt over newswatch's HTTP layer. Imported
    lazily to avoid a module import cycle with ``http`` (which imports this module)."""
    from newswatch.http import fetch_robots

    return RobotsGate(USER_AGENT, fetch_robots)


def _host_key(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def _robots_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
