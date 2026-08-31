import pytest
from thinchat.errors import ThinchatError

import newswatch._llm as _llm
from newswatch.errors import LLMError


def test_scrub_secrets_redacts_resolvable_key(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")
    scrubbed = _llm.scrub_secrets("HTTP 401 at https://api/v1?key=SECRET-KEY-123 rejected")
    assert "SECRET-KEY-123" not in scrubbed
    assert "***" in scrubbed


def test_make_llm_client_construction_error_hides_key(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")

    def boom(*args, **kwargs):
        raise ThinchatError("cannot initialise client with key SECRET-KEY-123")

    monkeypatch.setattr(_llm, "make_client", boom)
    with pytest.raises(LLMError) as excinfo:
        _llm.make_llm_client(max_tokens=100, action="summarizing")
    assert "SECRET-KEY-123" not in str(excinfo.value)


def test_make_llm_client_uses_credentials_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True)
    (cfg / "credentials.json").write_text('{"GEMINI_API_KEY": "file-key"}', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    captured: dict[str, object] = {}

    def fake_make_client(provider, *, model, api_key, max_tokens, max_retries):
        captured["provider"] = provider
        captured["api_key"] = api_key
        return object()

    monkeypatch.setattr(_llm, "make_client", fake_make_client)
    _llm.make_llm_client(max_tokens=100, action="summarizing")
    assert captured["provider"] == "gemini"
    assert captured["api_key"] == "file-key"


def test_make_llm_client_explicit_key_wins_over_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True)
    (cfg / "credentials.json").write_text('{"GEMINI_API_KEY": "file-key"}', encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        _llm, "make_client",
        lambda provider, *, model, api_key, max_tokens, max_retries: captured.setdefault("api_key", api_key),
    )
    _llm.make_llm_client(api_key="explicit", max_tokens=100, action="summarizing")
    assert captured["api_key"] == "explicit"


def test_make_llm_client_missing_key_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError):
        _llm.make_llm_client(max_tokens=100, action="summarizing")
