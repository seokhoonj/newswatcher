from typing import cast

import pytest
import requests

import newswatcher.http as http
from newswatcher.errors import FetchError
from newswatcher.robots import RobotsGate


class _Resp:
    def __init__(self, status=200, text="body", is_redirect=False, location=None):
        self.status_code = status
        self.text = text
        self.is_redirect = is_redirect
        self.headers = {"Location": location} if location else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


# --- get() enforces the robots gate before any request (INVARIANT 1) ---

def test_get_refuses_disallowed_url_without_requesting():
    calls = []

    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            calls.append(url)
            return _Resp()

    gate = RobotsGate("ua", lambda url: "User-agent: *\nDisallow: /")
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate, session=cast(requests.Session, _Session()))
    assert calls == []   # the disallowed URL was never fetched


def test_get_returns_text_when_allowed():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            return _Resp(200, "hello")

    gate = RobotsGate("ua", lambda url: None)   # no robots.txt -> allow
    assert http.get("https://e.com/x", gate, session=cast(requests.Session, _Session())) == "hello"


def test_get_raises_on_non_2xx():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            return _Resp(500, "")

    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate, session=cast(requests.Session, _Session()))


# --- get() re-gates every redirect hop, not just the first URL ---

def test_get_re_gates_a_redirect_and_refuses_a_disallowed_target():
    fetched = []

    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            fetched.append(url)
            return _Resp(302, is_redirect=True, location="https://e.com/private/x")

    gate = RobotsGate("ua", lambda url: "User-agent: *\nDisallow: /private")
    with pytest.raises(FetchError):
        http.get("https://e.com/ok", gate, session=cast(requests.Session, _Session()))
    assert fetched == ["https://e.com/ok"]   # the disallowed redirect target was never fetched


def test_get_follows_an_allowed_redirect_to_the_final_body():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            if url == "https://e.com/a":
                return _Resp(301, is_redirect=True, location="https://e.com/b")
            return _Resp(200, "final")

    gate = RobotsGate("ua", lambda url: None)
    assert http.get("https://e.com/a", gate, session=cast(requests.Session, _Session())) == "final"


def test_get_refuses_a_non_http_scheme_without_requesting():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            raise AssertionError("must not request a non-http(s) URL")

    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("file:///etc/passwd", gate, session=cast(requests.Session, _Session()))


def test_get_stops_on_a_redirect_loop():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            return _Resp(302, is_redirect=True, location="https://e.com/loop")

    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("https://e.com/loop", gate, session=cast(requests.Session, _Session()))


# --- get() manages the session it creates, and leaves an injected one to its owner ---

class _RecordingSession:
    def __init__(self):
        self.closed = False

    def get(self, url, timeout=None, allow_redirects=True):
        return _Resp(200, "ok")

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def test_get_closes_a_session_it_created(monkeypatch):
    created = _RecordingSession()
    monkeypatch.setattr(http, "new_session", lambda: created)
    gate = RobotsGate("ua", lambda url: None)
    http.get("https://e.com/x", gate)   # no session passed -> get() must create and close one
    assert created.closed is True


def test_get_does_not_close_an_injected_session():
    injected = _RecordingSession()
    gate = RobotsGate("ua", lambda url: None)
    http.get("https://e.com/x", gate, session=cast(requests.Session, injected))
    assert injected.closed is False   # the caller owns an injected session


def test_get_closes_a_created_session_even_on_request_failure(monkeypatch):
    class _FailingSession(_RecordingSession):
        def get(self, url, timeout=None, allow_redirects=True):
            return _Resp(500, "")   # raise_for_status will raise -> FetchError

    created = _FailingSession()
    monkeypatch.setattr(http, "new_session", lambda: created)
    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate)   # no session -> created, and closed on the error path
    assert created.closed is True


# --- fetch_robots: RFC 9309 fail-open on 4xx, fail-closed on 5xx / unreachable ---

def test_fetch_robots_4xx_allows(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(404, ""))
    assert http.fetch_robots("https://e.com/robots.txt") is None   # None -> gate allows


def test_fetch_robots_5xx_disallows(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(503, ""))
    text = http.fetch_robots("https://e.com/robots.txt")
    assert text is not None
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/anything") is False


def test_fetch_robots_unreachable_disallows(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(requests, "get", boom)
    text = http.fetch_robots("https://e.com/robots.txt")
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/anything") is False


def test_fetch_robots_200_returns_rules(monkeypatch):
    monkeypatch.setattr(requests, "get",
                        lambda *a, **k: _Resp(200, "User-agent: *\nDisallow: /private"))
    text = http.fetch_robots("https://e.com/robots.txt")
    gate = RobotsGate("ua", lambda url: text)
    assert gate.can_fetch("https://e.com/private/x") is False
    assert gate.can_fetch("https://e.com/public/x") is True


# --- get() fixes requests' latin-1 default for a charset-less text response ---

def test_charsetless_text_response_decoded_by_apparent_encoding():
    class _R:
        headers = {"Content-Type": "text/html"}
        encoding = "ISO-8859-1"
        apparent_encoding = "utf-8"

    r = _R()
    http._fix_charsetless_encoding(cast(requests.Response, r))
    assert r.encoding == "utf-8"   # detected, not the latin-1 default


def test_declared_charset_is_left_alone():
    class _R:
        headers = {"Content-Type": "text/html; charset=euc-kr"}
        encoding = "euc-kr"
        apparent_encoding = "utf-8"

    r = _R()
    http._fix_charsetless_encoding(cast(requests.Response, r))
    assert r.encoding == "euc-kr"   # a declared charset is trusted


# --- redirect + charset hardening (pin the behavior through the public get()) ---

def test_get_disables_automatic_redirect_following():
    seen = {}

    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            seen["allow_redirects"] = allow_redirects
            return _Resp(200, "ok")

    gate = RobotsGate("ua", lambda url: None)
    http.get("https://e.com/x", gate, session=cast(requests.Session, _Session()))
    assert seen["allow_redirects"] is False   # manual per-hop gating requires auto-follow OFF


def test_get_rejects_a_redirect_without_a_location():
    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            return _Resp(302, is_redirect=False)   # 3xx status but no Location header

    gate = RobotsGate("ua", lambda url: None)
    with pytest.raises(FetchError):
        http.get("https://e.com/x", gate, session=cast(requests.Session, _Session()))


def test_get_re_gates_a_cross_host_redirect_by_the_targets_own_robots():
    fetched = []

    def robots(url):
        return "User-agent: *\nDisallow: /" if "b.com" in url else None   # b.com forbids all

    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            fetched.append(url)
            return _Resp(302, is_redirect=True, location="https://b.com/x")

    gate = RobotsGate("ua", robots)
    with pytest.raises(FetchError):
        http.get("https://a.com/ok", gate, session=cast(requests.Session, _Session()))
    assert fetched == ["https://a.com/ok"]   # the cross-host target was gated before any fetch


def test_get_applies_apparent_encoding_through_the_public_path():
    class _R:
        status_code = 200
        is_redirect = False
        headers = {"Content-Type": "text/html"}   # no charset
        encoding = "ISO-8859-1"
        apparent_encoding = "utf-8"

        def raise_for_status(self):
            pass

        @property
        def text(self):
            return f"decoded-as-{self.encoding}"

    class _Session:
        def get(self, url, timeout=None, allow_redirects=True):
            return _R()

    gate = RobotsGate("ua", lambda url: None)
    out = http.get("https://e.com/x", gate, session=cast(requests.Session, _Session()))
    assert out == "decoded-as-utf-8"   # get() reset encoding to apparent_encoding before .text
