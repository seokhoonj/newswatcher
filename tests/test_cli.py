import argparse

import pytest

import newswatch.cli as cli


def test_watch_clamps_negative_sleep(monkeypatch):
    # When a poll overruns the interval, the next-tick time is already in the past, so
    # the naive (next_tick - now) is negative. time.sleep rejects a negative value with
    # ValueError -- which, not being a NewswatchError, would crash the watcher.
    monkeypatch.setattr(cli, "_run_poll", lambda a: 0)
    times = iter([0.0, 5000.0, 5000.5])   # init, post-poll (overran), pre-sleep
    monkeypatch.setattr("time.monotonic", lambda: next(times))
    slept = []

    class _Stop(Exception):
        pass

    def _sleep(seconds):
        slept.append(seconds)
        raise _Stop

    monkeypatch.setattr("time.sleep", _sleep)
    with pytest.raises(_Stop):
        cli._run_watch(argparse.Namespace(every=None))
    assert slept == [0.0]   # clamped to zero, never negative


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


def _capture_provider(monkeypatch):
    """Run poll with the LLM calls stubbed, recording the provider and model the CLI
    actually binds into the summarizer it hands to the pipeline (tested by invoking that
    summarizer, not by inspecting how it was bound)."""
    from newswatch.poll import PollReport
    from newswatch.summarize import Summary
    captured = {}

    def fake_summarize(item, body, *, provider, model, api_key=None):
        captured["provider"] = provider
        captured["model"] = model
        return Summary(title="t", link="u", text="x", model="m")

    def fake_poll_sources(*args, **kwargs):
        kwargs["summarize"](object(), "body")   # invoke it to exercise the binding
        return PollReport(collected=(), empty_crawl_sources=(), skipped=())

    monkeypatch.setattr(cli, "summarize_article", fake_summarize)
    monkeypatch.setattr(cli, "poll_sources", fake_poll_sources)
    return captured


def test_poll_binds_provider_and_model_from_flags(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store",
                     "--provider", "openai", "--model", "gpt-x"]) == 0
    assert captured == {"provider": "openai", "model": "gpt-x"}


def test_poll_provider_comes_from_environment_variable(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCH_LLM_PROVIDER", "claude")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    assert captured["provider"] == "claude"


def test_poll_model_comes_from_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("NEWSWATCH_LLM_MODEL", "configured-model")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    assert captured["model"] == "configured-model"


def test_poll_empty_provider_flag_falls_through_to_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCH_LLM_PROVIDER", "claude")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store", "--provider", ""]) == 0
    assert captured["provider"] == "claude"


def test_poll_defaults_to_gemini(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("NEWSWATCH_LLM_MODEL", raising=False)
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    from newswatch._llm import DEFAULT_PROVIDER
    assert captured["provider"] == DEFAULT_PROVIDER
    assert captured["model"] is None


def test_poll_unknown_provider_is_rejected(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    # a typo'd provider fails fast with a one-line error, even with nothing to summarize
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store",
                     "--provider", "gemninni"]) == 1


def test_heal_threads_provider_to_heal_source(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCH_LLM_PROVIDER", raising=False)
    from newswatch.sources import Source
    captured = {}

    def fake_heal_source(source, *, gate, apply, provider, model, **kwargs):
        captured["provider"] = provider
        captured["model"] = model
        return None

    monkeypatch.setattr(cli, "load_sources",
                        lambda: (Source("c", kind="crawl", url="u", topics=("t",),
                                        item="li", title="a", link="a@href"),))
    monkeypatch.setattr(cli, "heal_source", fake_heal_source)
    monkeypatch.setattr(cli, "default_gate", lambda: None)
    assert cli.main(["heal", "--provider", "openai", "--model", "gpt-x"]) == 0
    assert captured == {"provider": "openai", "model": "gpt-x"}
