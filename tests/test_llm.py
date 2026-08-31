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


def test_make_llm_client_hides_an_explicitly_passed_key(monkeypatch, tmp_path):
    # An api_key given in code is not in the env or credentials file, so scrub_secrets
    # cannot resolve it -- it must still be scrubbed from the message and the cause.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def boom(*args, **kwargs):
        raise ThinchatError("auth failed for key EXPLICIT-KEY-999")

    monkeypatch.setattr(_llm, "make_client", boom)
    with pytest.raises(LLMError) as excinfo:
        _llm.make_llm_client(api_key="EXPLICIT-KEY-999", max_tokens=100, action="summarizing")
    assert "EXPLICIT-KEY-999" not in str(excinfo.value)
    assert "EXPLICIT-KEY-999" not in str(excinfo.value.__cause__)


def test_scrub_exception_scrubs_the_whole_cause_chain(monkeypatch, tmp_path):
    import traceback
    secret = "SECRET-KEY-123"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", secret)
    # Build the key-bearing message from a variable so the *source line* the traceback
    # echoes does not itself contain the literal (that would be a test artifact, not a
    # scrub failure). A 3-deep chain with the key ONLY in the deepest link, reached via
    # both an implicit context (__context__) and an explicit cause (__cause__).
    deepest = f"GET https://api?key={secret} refused"
    try:
        try:
            try:
                raise OSError(deepest)
            except OSError:
                raise ValueError("transport failed")  # noqa: B904  # implicit __context__ is the point
        except ValueError as mid:
            raise ThinchatError("provider call failed") from mid   # explicit __cause__
    except ThinchatError as err:
        scrubbed = _llm.scrub_exception(err)
    # Assert against the actual rendered traceback, the real leak surface, not a re-walk.
    formatted = "".join(traceback.format_exception(scrubbed))
    assert secret not in formatted


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
