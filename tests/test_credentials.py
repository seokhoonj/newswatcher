import json

import pytest

from newswatch import credentials
from newswatch.errors import ConfigError


def _write_credentials(tmp_path, payload):
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True, exist_ok=True)
    path = cfg / "credentials.json"
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload,
                    encoding="utf-8")
    return path


def test_secret_from_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"GEMINI_API_KEY": "from-file"})
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert credentials.secret("GEMINI_API_KEY") == "from-file"


def test_env_wins_over_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"GEMINI_API_KEY": "from-file"})
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert credentials.secret("GEMINI_API_KEY") == "from-env"


def test_absent_file_is_no_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert credentials.secret("OPENAI_API_KEY") is None


def test_absent_key_in_file_is_no_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"GEMINI_API_KEY": "g"})
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    assert credentials.secret("CLAUDE_API_KEY") is None


def test_empty_value_is_no_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, {"GEMINI_API_KEY": ""})
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert credentials.secret("GEMINI_API_KEY") is None


def test_non_json_file_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, "{not json")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        credentials.secret("GEMINI_API_KEY")


def test_non_utf8_file_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "credentials.json").write_bytes(b"\xff\xfe not utf-8 bytes")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        credentials.secret("GEMINI_API_KEY")


@pytest.mark.parametrize("payload", [[], {"GEMINI_API_KEY": 123}])
def test_wrong_shape(monkeypatch, tmp_path, payload):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_credentials(tmp_path, payload)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    if isinstance(payload, list):
        with pytest.raises(ConfigError):
            credentials.secret("GEMINI_API_KEY")
    else:
        # a non-string value for the key reads as "no secret", not an error
        assert credentials.secret("GEMINI_API_KEY") is None
