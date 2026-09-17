import pytest
from thinchat.errors import ThinchatError

import newswatcher._llm as _llm
from newswatcher.errors import LLMError


class _FakeSecret:
    """A stand-in for thinchat's ``Secret``: reveals a plaintext, and is what the resolver returns.
    newswatcher's ``_llm`` only calls ``.reveal()`` on it."""

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value


def _stub_thinchat(monkeypatch, *, resolved):
    """Patch thinchat's resolver and client constructor (as ``_llm`` imported them) so a test drives
    ``make_llm_client`` without a store or a network. ``resolved`` is what the resolver returns when
    no override is given (a ``_FakeSecret`` or ``None``); an override always wins, as thinchat does
    it. Returns the dict the fake client records its ``provider`` / ``api_key`` in."""
    captured: dict[str, object] = {}

    def fake_get_api_key(provider, *, override=None):
        return _FakeSecret(override) if override is not None else resolved

    def fake_make_client(provider, *, model, api_key, max_tokens, max_retries):
        captured["provider"] = provider
        captured["api_key"] = api_key
        return object()

    monkeypatch.setattr(_llm, "get_api_key", fake_get_api_key)
    monkeypatch.setattr(_llm, "make_client", fake_make_client)
    return captured


def test_make_llm_client_uses_thinchats_resolved_key(monkeypatch):
    captured = _stub_thinchat(monkeypatch, resolved=_FakeSecret("stored-key"))
    _llm.make_llm_client(max_tokens=100, action="summarizing")
    assert captured["provider"] == "gemini"
    assert captured["api_key"] == "stored-key"


def test_make_llm_client_explicit_key_wins(monkeypatch):
    # An explicit override wins over whatever thinchat would otherwise resolve.
    captured = _stub_thinchat(monkeypatch, resolved=_FakeSecret("stored-key"))
    _llm.make_llm_client(api_key="explicit", max_tokens=100, action="summarizing")
    assert captured["api_key"] == "explicit"


def test_make_llm_client_ollama_needs_no_key(monkeypatch):
    # ollama is keyless: _llm never asks the resolver, and hands the client api_key=None.
    captured = _stub_thinchat(monkeypatch, resolved=None)
    _llm.make_llm_client(provider="ollama", max_tokens=100, action="summarizing")
    assert captured["api_key"] is None


def test_make_llm_client_missing_key_raises(monkeypatch):
    _stub_thinchat(monkeypatch, resolved=None)
    with pytest.raises(LLMError, match="needs an API key"):
        _llm.make_llm_client(max_tokens=100, action="summarizing")


def test_make_llm_client_unknown_provider_raises(monkeypatch):
    with pytest.raises(LLMError):
        _llm.make_llm_client(provider="nope", max_tokens=100, action="summarizing")


def test_make_llm_client_unreadable_store_becomes_llmerror(monkeypatch):
    # thinchat's resolver failing (a malformed store binding, an unreadable file) surfaces as a
    # newswatcher LLMError naming the action -- a foreign ThinchatError never escapes.
    def boom(provider, *, override=None):
        raise ThinchatError("store could not be read")

    monkeypatch.setattr(_llm, "get_api_key", boom)
    with pytest.raises(LLMError, match="could not read the stored key"):
        _llm.make_llm_client(max_tokens=100, action="summarizing")


def test_error_never_carries_the_resolved_key(monkeypatch):
    # newswatcher reveals the plaintext key to hand to the client; this pins that newswatcher's own
    # error composition never surfaces it. The stubbed ThinchatError is contract-compliant (thinchat
    # scrubs its own errors), so this asserts newswatcher's surface only, and re-scrubs nothing.
    def boom(provider, *, model, api_key, max_tokens, max_retries):
        raise ThinchatError("provider rejected the request")   # a real one carries no key

    monkeypatch.setattr(_llm, "get_api_key", lambda p, *, override=None: _FakeSecret("file-key"))
    monkeypatch.setattr(_llm, "make_client", boom)
    with pytest.raises(LLMError) as excinfo:
        _llm.make_llm_client(max_tokens=100, action="summarizing")
    surfaces = []
    err: BaseException | None = excinfo.value
    while err is not None:
        surfaces.append(str(err))
        err = err.__cause__
    assert all("file-key" not in text for text in surfaces)


def test_provider_key_name_maps_known_and_keyless():
    assert _llm.provider_key_name("gemini") == "GEMINI_API_KEY"
    assert _llm.provider_key_name("ollama") is None
