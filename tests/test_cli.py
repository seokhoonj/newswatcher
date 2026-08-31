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


def test_watch_survives_a_transient_poll_error(monkeypatch):
    # A DigestError/LLMError/ConfigError from one poll must not kill the watcher: the
    # resilience design ("re-collect and re-send next run") depends on there being a next
    # run, which watch only has if it stays in the loop.
    from newswatch.errors import LLMError
    calls = []

    class _Stop(Exception):
        pass

    def fake_poll(a):
        calls.append(1)
        if len(calls) == 1:
            raise LLMError("transient provider blip")
        raise _Stop   # break the loop on the 2nd tick

    monkeypatch.setattr(cli, "_run_poll", fake_poll)
    monkeypatch.setattr("time.monotonic", lambda: 0.0)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(_Stop):
        cli._run_watch(argparse.Namespace(every=None))
    assert len(calls) == 2   # it continued to a 2nd poll after the 1st raised


def test_heal_continues_past_a_failing_source(monkeypatch, capsys):
    # The package invariant "one bad source must not stop the rest" must hold for the
    # manual heal command too, not just the in-poll healer.
    from newswatch.errors import FetchError
    from newswatch.heal import HealResult
    from newswatch.sources import Source

    srcs = (Source("a", kind="crawl", url="u", item="i", title="t", link="l"),
            Source("b", kind="crawl", url="u", item="i", title="t", link="l"))
    monkeypatch.setattr(cli, "load_sources", lambda: srcs)
    monkeypatch.setattr(cli, "_resolve_llm_choice", lambda a: ("gemini", None))
    seen = []

    def fake_heal(source, **kwargs):
        seen.append(source.name)
        if source.name == "a":
            raise FetchError("listing returned 500")
        return HealResult(source_name="b", old={}, new={}, applied=True, note="repaired 'b'")

    monkeypatch.setattr(cli, "heal_source", fake_heal)
    code = cli._run_heal(argparse.Namespace(dry_run=False))
    assert code == 0
    assert seen == ["a", "b"]   # b was still attempted after a failed
    captured = capsys.readouterr()
    assert "repaired 'b'" in captured.out
    assert "a" in captured.err   # the failure was reported to stderr, not fatal


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


def _poll_returning_one(monkeypatch):
    """Stub the pipeline to return one collected article and record write_state calls."""
    from newswatch.poll import PollReport
    from newswatch.store import Article
    article = Article(guid="g1", title="t", link="https://e.com/1", source_name="s",
                      published="2026-08-15T00:00:00Z", topics=("markets",), summary="x")
    writes = []
    monkeypatch.setattr(cli, "poll_sources",
                        lambda *a, **k: PollReport(collected=(article,),
                                                   empty_crawl_sources=(), skipped=()))
    monkeypatch.setattr(cli, "write_state", lambda *a, **k: writes.append(1))
    monkeypatch.setattr(cli, "read_state", lambda *a, **k: object())
    return writes


def test_poll_does_not_persist_state_when_mail_fails(monkeypatch, tmp_path):
    from newswatch.errors import DigestError
    _xdg(monkeypatch, tmp_path)
    writes = _poll_returning_one(monkeypatch)

    def _boom(*a, **k):
        raise DigestError("smtp down")

    monkeypatch.setattr(cli, "send_digest", _boom)
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert writes == []   # watermark not advanced, so the digest re-sends next run


def test_poll_persists_state_after_successful_mail(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    writes = _poll_returning_one(monkeypatch)
    sent = []
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: sent.append(1))
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 0
    assert sent == [1] and writes == [1]


def test_poll_skips_when_another_is_running(monkeypatch, tmp_path, capsys):
    from newswatch.lock import single_instance
    _xdg(monkeypatch, tmp_path)
    ran = []

    def _poll_once(a):
        ran.append(1)
        return 0

    monkeypatch.setattr(cli, "_poll_once", _poll_once)
    with single_instance("poll"):   # stand in for another poll already holding the lock
        assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    assert ran == []   # the poll body did not run
    assert "already running" in capsys.readouterr().err


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
        return Summary(text="x", model="m")

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
