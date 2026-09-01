"""One HTTP layer for newswatcher: a shared requests session, an identifying
User-Agent, and a ``get`` that refuses any URL the robots gate disallows before a
request is made. Every feed, listing, and body fetch goes through here, so the
robots rule is enforced in one place rather than at each call site."""

from __future__ import annotations

import contextlib
from urllib.parse import urljoin, urlsplit

import requests

from newswatcher.errors import FetchError
from newswatcher.robots import USER_AGENT, RobotsGate

__all__ = ["new_session", "get", "fetch_robots", "default_gate"]

_TIMEOUT = 20.0
_MAX_REDIRECTS = 5

# A synthetic robots.txt that forbids everything, returned when robots.txt could not be
# fetched because the server erred (5xx) or was unreachable. RFC 9309 requires a client
# to assume a complete disallow in that case, so the gate parses these rules and refuses
# the host for the run rather than treating the failure as allow-all.
_DISALLOW_ALL = "User-agent: *\nDisallow: /"


def new_session() -> requests.Session:
    """A requests session carrying newswatcher's User-Agent, reused across a poll's
    fetches so connections are pooled."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def get(url: str, gate: RobotsGate, *, session: requests.Session | None = None,
        timeout: float = _TIMEOUT) -> str:
    """Fetch ``url`` as text, checking the robots gate before every request. Redirects are
    followed manually so each hop is re-gated and confined to http/https: a URL that
    301/302s to a Disallow path, another host, or a non-web scheme cannot smuggle a fetch
    past robots.txt (requests' automatic redirect following checks only the first URL).

    Raises:
        FetchError: robots.txt disallows the URL or a redirect hop, a hop leaves
            http/https, there are too many redirects, or the request failed / returned a
            non-2xx status.
    """
    # Close only a session we created; an injected one belongs to the caller (a poll
    # threads one pooled session through all its fetches).
    manage = contextlib.nullcontext(session) if session is not None else new_session()
    try:
        with manage as http:
            response = _fetch_gated(http, url, gate, timeout)
    except requests.RequestException as err:
        raise FetchError(f"could not fetch {url}: {err}") from err
    _fix_charsetless_encoding(response)
    return response.text


def _fix_charsetless_encoding(response: requests.Response) -> None:
    """requests decodes a ``text/*`` body whose Content-Type carries no charset as
    ISO-8859-1. Many older Korean news pages (EUC-KR or UTF-8) send no header charset, so
    that default turns the listing/body into mojibake that then flows into the LLM summary
    and the digest. When the header omits a charset, decode by the bytes' own detected
    encoding instead; a declared charset is trusted and left alone."""
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type.startswith("text/") and "charset=" not in content_type:
        response.encoding = response.apparent_encoding


def _fetch_gated(http: requests.Session, url: str, gate: RobotsGate,
                 timeout: float) -> requests.Response:
    """GET ``url`` following redirects by hand, re-running the gate and scheme check on the
    original URL and every ``Location``. Returns the final non-redirect response."""
    for _ in range(_MAX_REDIRECTS + 1):
        _require_fetchable(url, gate)
        response = http.get(url, timeout=timeout, allow_redirects=False)
        if response.is_redirect:   # 3xx with a Location -> re-gate the target, do not follow
            url = urljoin(url, response.headers["Location"])
            continue
        if 300 <= response.status_code < 400:
            # a redirect status with no Location -- raise_for_status ignores 3xx, so guard it
            # here rather than hand the interstitial stub body to the summarizer
            raise FetchError(f"redirect without a Location fetching {url}")
        response.raise_for_status()
        return response
    raise FetchError(f"too many redirects fetching {url}")


def _require_fetchable(url: str, gate: RobotsGate) -> None:
    """Confine ``url`` to http/https and pass it through the robots gate and the host's
    Crawl-delay before any request -- applied per hop, not just to the first URL."""
    if urlsplit(url).scheme not in ("http", "https"):
        raise FetchError(f"refusing to fetch non-http(s) URL {url}")
    if not gate.can_fetch(url):
        raise FetchError(f"robots.txt disallows fetching {url}")
    gate.throttle(url)   # honor the host's requested Crawl-delay between fetches


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
