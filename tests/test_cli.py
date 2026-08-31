import newswatch.cli as cli


def _xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("NEWSWATCH_DATA_DIR", raising=False)
    monkeypatch.delenv("NEWSWATCH_STATE_DIR", raising=False)


def test_add_topic_then_list(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    assert cli.main(["add-topic", "insurance", "--include", "보험", "손보"]) == 0
    assert cli.main(["topics"]) == 0
    out = capsys.readouterr().out
    assert "insurance" in out


def test_add_source_rss_then_list(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    code = cli.main(["add-source", "한국보험신문",
                     "https://www.insnews.co.kr/rss/allArticle.xml",
                     "--kind", "rss", "--topic", "insurance", "--keep-all"])
    assert code == 0
    cli.main(["sources"])
    assert "한국보험신문" in capsys.readouterr().out


def test_add_crawl_source_requires_selectors(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    # missing --item/--title/--link -> one-line error, exit 1
    code = cli.main(["add-source", "x", "https://e.com/list",
                     "--kind", "crawl", "--topic", "t"])
    assert code == 1


def test_unknown_command_exits_nonzero(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    code = cli.main(["frobnicate"])
    assert code != 0


def _capture_summarizer(monkeypatch):
    """Stub poll_sources to record the summarizer it is handed and report nothing."""
    from newswatch.poll import PollReport
    captured = {}

    def fake_poll_sources(*args, **kwargs):
        captured["summarize"] = kwargs["summarize"]
        return PollReport((), (), ())

    monkeypatch.setattr(cli, "poll_sources", fake_poll_sources)
    return captured


def test_poll_provider_flag_binds_summarizer(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    captured = _capture_summarizer(monkeypatch)
    code = cli.main(["poll", "--no-mail", "--no-heal", "--no-store",
                     "--provider", "openai", "--model", "gpt-x"])
    assert code == 0
    assert captured["summarize"].keywords["provider"] == "openai"
    assert captured["summarize"].keywords["model"] == "gpt-x"


def test_poll_provider_from_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCH_LLM_PROVIDER", "claude")
    captured = _capture_summarizer(monkeypatch)
    code = cli.main(["poll", "--no-mail", "--no-heal", "--no-store"])
    assert code == 0
    assert captured["summarize"].keywords["provider"] == "claude"


def test_poll_provider_defaults_to_gemini(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("NEWSWATCH_LLM_MODEL", raising=False)
    captured = _capture_summarizer(monkeypatch)
    code = cli.main(["poll", "--no-mail", "--no-heal", "--no-store"])
    assert code == 0
    from newswatch._llm import DEFAULT_PROVIDER
    assert captured["summarize"].keywords["provider"] == DEFAULT_PROVIDER
    assert captured["summarize"].keywords["model"] is None
