import pytest
import requests

import newswatch.http as http
from newswatch.errors import FetchError
from newswatch.robots import RobotsGate


class _Resp:
    def __init__(self, status=200, text="body"):
        self.status_code = status
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


# --- get() enforces the robots gate before any request (INVARIANT 1) ---

def test_get_refuses_disallowed_url_without_requesting():
    calls = []

    class _Session:
        def get(self, url, timeout=None):
            calls.append(url)
            return _Resp()

    gate = RobotsGate("ua", lambda url: "User-agent: *\nDisallow: /")
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate, session=_Session())
    assert calls == []   # the disallowed URL was never fetched


def test_get_returns_text_when_allowed():
    class _Session:
        def get(self, url, timeout=None):
            return _Resp(200, "hello")

    gate = RobotsGate("ua", lambda url: None)   # no robots.txt -> allow
    assert http.get("https://e.com/x", gate, session=_Session()) == "hello"


def test_get_raises_on_non_2xx():
    class _Session:
        def get(self, url, timeout=None):
            return _Resp(500, "")

    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate, session=_Session())


# --- fetch_robots: RFC 9309 fail-open on 4xx, fail-closed on 5xx / unreachable ---

def test_fetch_robots_4xx_allows(monkeypatch):
    monkeypatch.setattr(http.requests, "get", lambda *a, **k: _Resp(404, ""))
    assert http.fetch_robots("https://e.com/robots.txt") is None   # None -> gate allows


def test_fetch_robots_5xx_disallows(monkeypatch):
    monkeypatch.setattr(http.requests, "get", lambda *a, **k: _Resp(503, ""))
    text = http.fetch_robots("https://e.com/robots.txt")
    assert text is not None
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/anything") is False


def test_fetch_robots_unreachable_disallows(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(http.requests, "get", boom)
    text = http.fetch_robots("https://e.com/robots.txt")
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/anything") is False


def test_fetch_robots_200_returns_rules(monkeypatch):
    monkeypatch.setattr(http.requests, "get",
                        lambda *a, **k: _Resp(200, "User-agent: *\nDisallow: /private"))
    text = http.fetch_robots("https://e.com/robots.txt")
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/private/x") is False
    assert gate.can_fetch("https://e.com/public/x") is True
