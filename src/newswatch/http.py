"""One HTTP layer for newswatch: a shared requests session, an identifying
User-Agent, and a ``get`` that refuses any URL the robots gate disallows before a
request is made. Every feed, listing, and body fetch goes through here, so the
robots rule is enforced in one place rather than at each call site."""

from __future__ import annotations

import contextlib

import requests

from newswatch.errors import FetchError
from newswatch.robots import USER_AGENT, RobotsGate

__all__ = ["new_session", "get", "fetch_robots", "default_gate"]

_TIMEOUT = 20.0

# A synthetic robots.txt that forbids everything, returned when robots.txt could not be
# fetched because the server erred (5xx) or was unreachable. RFC 9309 requires a client
# to assume a complete disallow in that case, so the gate parses these rules and refuses
# the host for the run rather than treating the failure as allow-all.
_DISALLOW_ALL = "User-agent: *\nDisallow: /"


def new_session() -> requests.Session:
    """A requests session carrying newswatch's User-Agent, reused across a poll's
    fetches so connections are pooled."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def get(url: str, gate: RobotsGate, *, session: requests.Session | None = None,
        timeout: float = _TIMEOUT) -> str:
    """Fetch ``url`` as text, first checking the robots gate. A disallowed URL is
    never requested.

    Raises:
        FetchError: robots.txt disallows the URL, or the request failed / returned a
            non-2xx status.
    """
    if not gate.can_fetch(url):
        raise FetchError(f"robots.txt disallows fetching {url}")
    gate.throttle(url)   # honor the host's requested Crawl-delay between fetches
    # Close only a session we created; an injected one belongs to the caller (a poll
    # threads one pooled session through all its fetches).
    manage = contextlib.nullcontext(session) if session is not None else new_session()
    try:
        with manage as http:
            response = http.get(url, timeout=timeout)
            response.raise_for_status()
    except requests.RequestException as err:
        raise FetchError(f"could not fetch {url}: {err}") from err
    return response.text


def fetch_robots(robots_url: str) -> str | None:
    """Fetch a host's robots.txt for the gate. Not itself robots-gated (fetching
    robots.txt is always permitted). Following RFC 9309:

    - 2xx: return the rules text.
    - 4xx (no robots.txt): return None -- the gate treats this as allow-all.
    - 5xx or unreachable: return a disallow-all robots.txt -- the gate must assume a
      complete disallow when the server errs or cannot be reached.
    """
    try:
        response = requests.get(robots_url, timeout=_TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
    except requests.RequestException:
        return _DISALLOW_ALL
    if response.status_code >= 500:
        return _DISALLOW_ALL
    if response.status_code >= 400:
        return None
    return response.text


def default_gate() -> RobotsGate:
    """A robots gate whose fetcher pulls robots.txt over this HTTP layer. Lives here,
    beside ``fetch_robots``, so ``robots`` needs no import of ``http`` (no cycle)."""
    return RobotsGate(USER_AGENT, fetch_robots)
