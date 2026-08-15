import newswatch.config as config


def test_dirs_follow_xdg_env(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("NEWSWATCH_DATA_DIR", raising=False)
    monkeypatch.delenv("NEWSWATCH_STATE_DIR", raising=False)
    assert config.config_dir() == tmp_path / "cfg" / "newswatch"
    assert config.data_dir() == tmp_path / "data" / "newswatch"
    assert config.state_dir() == tmp_path / "state" / "newswatch"


def test_setting_prefers_env_then_file(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg = tmp_path / "newswatch"
    cfg.mkdir(parents=True)
    (cfg / "config.toml").write_text('digest_to = "me"\n', encoding="utf-8")
    monkeypatch.delenv("NEWSWATCH_DIGEST_TO", raising=False)
    assert config.setting("NEWSWATCH_DIGEST_TO") == "me"
    monkeypatch.setenv("NEWSWATCH_DIGEST_TO", "boss")
    assert config.setting("NEWSWATCH_DIGEST_TO") == "boss"


def test_data_dir_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("NEWSWATCH_DATA_DIR", str(tmp_path / "elsewhere"))
    assert config.data_dir() == tmp_path / "elsewhere"
