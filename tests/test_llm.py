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
    # The chained cause must also be scrubbed: logging.exception formats the whole
    # __cause__/__context__ chain, so a raw key there defeats the redaction.
    assert "SECRET-KEY-123" not in str(excinfo.value.__cause__)


def test_scrub_exception_scrubs_the_whole_cause_chain(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")
    # A provider error (ThinchatError) whose own cause (a transport error) embeds the
    # key in a URL -- the realistic Gemini shape.
    try:
        try:
            raise ValueError("GET https://api?key=SECRET-KEY-123 failed")
        except ValueError as transport:
            raise ThinchatError("provider call failed") from transport
    except ThinchatError as err:
        scrubbed = _llm.scrub_exception(err)
    chain = []
    node: BaseException | None = scrubbed
    while node is not None:
        chain.append(str(node))
        node = node.__cause__ or node.__context__
    assert not any("SECRET-KEY-123" in link for link in chain)


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


def test_make_llm_client_env_key_wins_over_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True)
    (cfg / "credentials.json").write_text('{"GEMINI_API_KEY": "file-key"}', encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "env-key")

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        _llm, "make_client",
        lambda provider, *, model, api_key, max_tokens, max_retries: captured.setdefault("api_key", api_key),
    )
    _llm.make_llm_client(max_tokens=100, action="summarizing")
    assert captured["api_key"] == "env-key"


def test_make_llm_client_ollama_needs_no_key(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    # ollama has no entry in ENV_BY_PROVIDER, so no key is required or looked up
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        _llm, "make_client",
        lambda provider, *, model, api_key, max_tokens, max_retries: captured.setdefault("api_key", api_key),
    )
    _llm.make_llm_client(provider="ollama", max_tokens=100, action="summarizing")
    assert captured["api_key"] is None


def test_make_llm_client_missing_key_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError):
        _llm.make_llm_client(max_tokens=100, action="summarizing")
