"""One HTTP layer for newswatch: a shared requests session, an identifying
User-Agent, and a ``get`` that refuses any URL the robots gate disallows before a
request is made. Every feed, listing, and body fetch goes through here, so the
robots rule is enforced in one place rather than at each call site."""

from __future__ import annotations

import requests

from newswatch.errors import FetchError
from newswatch.robots import USER_AGENT, RobotsGate

__all__ = ["new_session", "get", "fetch_robots"]

_TIMEOUT = 20.0


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
    http = session or new_session()
    try:
        response = http.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as err:
        raise FetchError(f"could not fetch {url}: {err}") from err
    return response.text


def fetch_robots(robots_url: str) -> str | None:
    """Fetch a host's robots.txt for the gate. Returns the text, or None when the host
    has no robots.txt (a 4xx) or it could not be fetched — both mean 'no rules', which
    the gate treats as allow-all. Not itself robots-gated (fetching robots.txt is
    always permitted)."""
    try:
        response = requests.get(robots_url, timeout=_TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
    except requests.RequestException:
        return None
    if response.status_code >= 400:
        return None
    return response.text
