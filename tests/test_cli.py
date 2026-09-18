import argparse

import pytest

import newswatcher.cli as cli
from newswatcher import credentials


def test_watch_clamps_negative_sleep(monkeypatch):
    # When a poll overruns the interval, the next-tick time is already in the past, so
    # the naive (next_tick - now) is negative. time.sleep rejects a negative value with
    # ValueError -- which, not being a NewswatcherError, would crash the watcher.
    monkeypatch.setattr(cli, "_run_poll", lambda a: 0)
    monkeypatch.setattr(cli, "_resolve_llm_choice", lambda a: ("gemini", None))
    monkeypatch.setattr(cli, "_resolve_dedup_threshold", lambda: 0.5)
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
    from newswatcher.errors import LLMError
    calls = []

    class _Stop(Exception):
        pass

    def fake_poll(a):
        calls.append(1)
        if len(calls) == 1:
            raise LLMError("transient provider blip")
        raise _Stop   # break the loop on the 2nd tick

    monkeypatch.setattr(cli, "_run_poll", fake_poll)
    monkeypatch.setattr(cli, "_resolve_llm_choice", lambda a: ("gemini", None))
    monkeypatch.setattr(cli, "_resolve_dedup_threshold", lambda: 0.5)
    monkeypatch.setattr("time.monotonic", lambda: 0.0)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(_Stop):
        cli._run_watch(argparse.Namespace(every=None))
    assert len(calls) == 2   # it continued to a 2nd poll after the 1st raised


def test_heal_continues_past_a_failing_source(monkeypatch, capsys):
    # The package invariant "one bad source must not stop the rest" must hold for the
    # manual heal command too, not just the in-poll healer.
    from newswatcher.errors import FetchError
    from newswatcher.heal import HealResult
    from newswatcher.sources import Source

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
    monkeypatch.delenv("NEWSWATCHER_DATA_DIR", raising=False)
    monkeypatch.delenv("NEWSWATCHER_STATE_DIR", raising=False)


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


def test_set_key_stores_the_prompted_key(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "typed-key")
    assert cli.main(["set-key", "gemini"]) == 0
    assert "typed-key" not in capsys.readouterr().out   # the value is confirmed, never echoed
    import thinchat
    resolved = thinchat.get_api_key("gemini")   # the key lands in thinchat's store, not newswatcher's
    assert resolved is not None and resolved.reveal() == "typed-key"


def test_set_key_rejects_an_unknown_provider(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    # A typo is rejected before the prompt: getpass must never be reached.
    monkeypatch.setattr("getpass.getpass",
                        lambda prompt="": pytest.fail("should not prompt for an unknown provider"))
    assert cli.main(["set-key", "nope"]) == 1


def test_set_key_rejects_a_keyless_provider(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setattr("getpass.getpass",
                        lambda prompt="": pytest.fail("should not prompt for a keyless provider"))
    assert cli.main(["set-key", "ollama"]) == 1


def test_set_key_rejects_a_blank_entry(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "   ")
    assert cli.main(["set-key", "gemini"]) == 2   # blank entry -> usage error, stores nothing
    import thinchat
    assert thinchat.get_api_key("gemini") is None


def test_set_key_handles_closed_stdin(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def _eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("getpass.getpass", _eof)
    assert cli.main(["set-key", "gemini"]) == 2   # stdin closed -> usage error, stores nothing
    import thinchat
    assert thinchat.get_api_key("gemini") is None


def test_doctor_exits_nonzero_when_the_llm_key_is_missing(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert cli.main(["doctor"]) == 1   # a configured channel (LLM) has no secret
    out = capsys.readouterr().out
    assert "credentials" in out and "not set" in out
    assert "thinchat/credentials.json" in out   # the store path is shown, not hidden


def test_doctor_exits_zero_when_everything_configured_is_set(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import thinchat
    thinchat.set_api_key("gemini", value="a-key")   # LLM set; email/chat unconfigured (not counted)
    assert cli.main(["doctor"]) == 0


def test_setup_fills_the_missing_llm_key(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "wizard-key")
    assert cli.main(["setup"]) == 0   # LLM filled; email/chat unconfigured are reported, not failed
    captured = capsys.readouterr()
    assert "wizard-key" not in captured.out and "wizard-key" not in captured.err   # never echoed
    import thinchat
    resolved = thinchat.get_api_key("gemini")
    assert resolved is not None and resolved.reveal() == "wizard-key"


def test_setup_continues_after_one_channel_fails(monkeypatch, tmp_path, capsys):
    # setup's promised per-channel isolation: a failed setter is reported and the next channel
    # still runs. Two MISSING channels; the first setter raises, the second must still store.
    _xdg(monkeypatch, tmp_path)
    from newswatcher.credentials import Channel, ChannelState
    from newswatcher.errors import ConfigError

    recorded: dict[str, str] = {}

    def fail_setter(value):
        raise ConfigError("the first channel's store is broken")

    def ok_setter(value):
        recorded["second"] = value

    channels = [
        Channel("first", "toolA", "~/a", ChannelState.MISSING, setter=fail_setter),
        Channel("second", "toolB", "~/b", ChannelState.MISSING, setter=ok_setter),
    ]
    monkeypatch.setattr(credentials, "channels", lambda provider: channels)
    monkeypatch.setattr(credentials, "legacy_llm_store", lambda: None)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "value")
    assert cli.main(["setup"]) == 1   # one channel failed -> non-zero
    assert recorded["second"] == "value"   # ...but the second channel still ran
    assert "first" in capsys.readouterr().err   # the failure was reported


def test_doctor_shows_a_not_installed_channel(monkeypatch, tmp_path, capsys):
    # A delivery extra that is not installed shows as "not installed" with an install hint, and
    # does NOT count toward the non-zero exit (it is a deliberate opt-out, like an unconfigured one).
    import sys

    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import thinchat
    thinchat.set_api_key("gemini", value="k")            # LLM set, so exit hinges on delivery
    monkeypatch.setitem(sys.modules, "mailmail", None)   # newswatcher[email] absent
    assert cli.main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "not installed" in out and "pip install newswatcher[email]" in out


def test_mark_by_state_covers_every_channel_state():
    # doctor indexes _MARK_BY_STATE by the channel's state; a new ChannelState member without a
    # mark would KeyError at runtime. Pin the coverage so it fails at test time instead.
    from newswatcher.credentials import ChannelState

    assert set(cli._MARK_BY_STATE) == set(ChannelState)


def test_doctor_reports_an_unreadable_store_as_error_without_leaking(monkeypatch, tmp_path, capsys):
    # An unreadable store makes the channel ERROR (counted -> exit 1); the mark shows "error" and
    # the tool's (possibly secret-bearing) message is never rendered.
    import thinchat
    from thinchat.errors import ThinchatError

    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    sentinel = "SENTINEL-store-detail"

    def boom(provider, **kwargs):
        raise ThinchatError(sentinel)

    monkeypatch.setattr(thinchat, "get_api_key", boom)
    assert cli.main(["doctor"]) == 1
    captured = capsys.readouterr()
    assert "error" in captured.out
    assert sentinel not in captured.out and sentinel not in captured.err


def test_set_key_reports_a_storage_failure_without_leaking(monkeypatch, tmp_path, capsys):
    import thinchat
    from thinchat.errors import ThinchatError

    _xdg(monkeypatch, tmp_path)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "SENTINEL-typed-key")

    def boom(provider, *, value):
        raise ThinchatError("store write failed")   # scrubbed: no key

    monkeypatch.setattr(thinchat, "set_api_key", boom)
    assert cli.main(["set-key", "gemini"]) == 1   # storage failure -> LLMError -> exit 1
    captured = capsys.readouterr()
    assert "SENTINEL-typed-key" not in captured.out and "SENTINEL-typed-key" not in captured.err


def test_doctor_never_prints_the_stored_secret(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import thinchat
    thinchat.set_api_key("gemini", value="super-secret-value")
    assert cli.main(["doctor"]) == 0
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "super-secret-value" not in captured.err


def test_setup_skips_a_channel_when_no_value_is_entered(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")   # empty -> skip, store nothing
    assert cli.main(["setup"]) == 0
    import thinchat
    assert thinchat.get_api_key("gemini") is None


def test_setup_points_at_the_migration_for_a_lingering_legacy_store(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    import credbox
    credbox.Credentials("newswatcher").set("GEMINI_API_KEY", value="old-key")
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")
    cli.main(["setup"])
    captured = capsys.readouterr()
    # the full, runnable command is shown -- not a partial fragment
    assert ("credbox migrate --from-app newswatcher --to-app thinchat --remove-source"
            in captured.out)
    assert "old-key" not in captured.out and "old-key" not in captured.err   # never the value


def _poll_returning_one(monkeypatch):
    """Stub the pipeline to return one collected article and record write_state calls."""
    from newswatcher.poll import PollReport
    from newswatcher.store import Article
    article = Article(guid="g1", title="t", link="https://e.com/1", source_name="s",
                      published="2026-08-15T00:00:00Z", topics=("markets",), summary="x")
    writes = []
    monkeypatch.setattr(cli, "poll_sources",
                        lambda *a, **k: PollReport(collected=(article,),
                                                   empty_crawl_sources=(), skipped=()))
    monkeypatch.setattr(cli, "write_state", lambda *a, **k: writes.append(1))
    monkeypatch.setattr(cli, "read_state", lambda *a, **k: object())
    return writes


def _record_prune_calls(monkeypatch) -> list[int]:
    """Replace FileStore.prune_older_than with a recorder; return the list of keep_days
    it was called with (empty when the poll never prunes)."""
    from newswatcher.store import FileStore
    calls: list[int] = []

    def _record(self, keep_days):
        calls.append(keep_days)
        return 0

    monkeypatch.setattr(FileStore, "prune_older_than", _record)
    return calls


def _stub_send_digest(record: list[int]):
    """A send_digest double that records each call and reports no delivery failures."""
    def _send(*args, **kwargs):
        record.append(1)
        return ()
    return _send


def test_poll_does_not_persist_state_when_mail_fails(monkeypatch, tmp_path):
    from newswatcher.errors import DigestError
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
    sent: list[int] = []
    monkeypatch.setattr(cli, "send_digest", _stub_send_digest(sent))
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 0
    assert sent == [1] and writes == [1]


def test_poll_persists_watermark_after_a_partial_delivery_failure(monkeypatch, tmp_path, capsys):
    # One channel delivered, the other failed: send_digest RETURNS the failure (does not
    # raise), so the watermark still advances -- the delivered channel is not re-sent next run.
    _xdg(monkeypatch, tmp_path)
    writes = _poll_returning_one(monkeypatch)
    monkeypatch.setattr(cli, "send_digest",
                        lambda *a, **k: ("could not send digest to chat: route down",))
    assert cli.main(["poll", "--no-heal", "--no-store",
                     "--to", "you@example.com", "--push", "alerts"]) == 0
    assert writes == [1]                                    # watermark advanced despite the failure
    assert "route down" in capsys.readouterr().err


def test_poll_routes_both_email_and_chat_flags_to_the_digest(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    _poll_returning_one(monkeypatch)
    calls: dict[str, object] = {}
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: calls.update(k) or ())
    assert cli.main(["poll", "--no-heal", "--no-store",
                     "--to", "you@example.com", "--push", "alerts"]) == 0
    assert calls["email_to"] == "you@example.com"
    assert calls["push_to"] == "alerts"


def test_poll_can_send_to_chat_alone(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_DIGEST_TO", raising=False)
    _poll_returning_one(monkeypatch)
    calls: dict[str, object] = {}
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: calls.update(k) or ())
    assert cli.main(["poll", "--no-heal", "--no-store", "--push", "alerts"]) == 0
    assert calls["email_to"] is None and calls["push_to"] == "alerts"


def test_poll_warns_and_sends_nothing_when_no_destination_is_configured(
    monkeypatch, tmp_path, capsys
):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_DIGEST_TO", raising=False)
    monkeypatch.delenv("NEWSWATCHER_DIGEST_PUSH", raising=False)
    _poll_returning_one(monkeypatch)
    sent: list[int] = []
    monkeypatch.setattr(cli, "send_digest", _stub_send_digest(sent))
    assert cli.main(["poll", "--no-heal", "--no-store"]) == 0
    assert sent == []                                       # nothing delivered
    assert "no digest destination" in capsys.readouterr().err


def test_poll_reads_the_dedup_threshold_from_the_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_DEDUP_THRESHOLD", "0.8")
    _poll_returning_one(monkeypatch)
    seen: dict[str, float] = {}
    monkeypatch.setattr(cli, "group_stories",
                        lambda arts, *, threshold: seen.update(threshold=threshold) or ())
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: ())
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 0
    assert seen["threshold"] == 0.8


def test_poll_rejects_a_nonnumeric_dedup_threshold(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_DEDUP_THRESHOLD", "aggressive")
    _poll_returning_one(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert "NEWSWATCHER_DEDUP_THRESHOLD" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["-1", "2.0", "nan", "inf", "-inf"])
def test_poll_rejects_an_out_of_range_or_nonfinite_dedup_threshold(
    monkeypatch, tmp_path, capsys, bad
):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_DEDUP_THRESHOLD", bad)
    _poll_returning_one(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert "NEWSWATCHER_DEDUP_THRESHOLD" in capsys.readouterr().err


def test_poll_validates_the_dedup_threshold_before_spending_the_llm(monkeypatch, tmp_path):
    # A malformed threshold must fail before poll_sources runs (which pays the LLM to
    # summarize), not after -- else every watch tick re-spends before re-failing.
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_DEDUP_THRESHOLD", "nonsense")
    spent = []
    monkeypatch.setattr(cli, "poll_sources", lambda *a, **k: spent.append(1))
    monkeypatch.setattr(cli, "read_state", lambda *a, **k: object())
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert spent == []   # the paid poll was never reached


def test_watch_ends_instead_of_looping_on_a_permanent_config_error(monkeypatch, tmp_path):
    # A permanent bad threshold must end the watch (exit 1), not loop forever re-failing
    # while never delivering: the pre-flight resolution raises before the loop body runs.
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_DEDUP_THRESHOLD", "nonsense")
    ran = []
    monkeypatch.setattr(cli, "_run_poll", lambda a: ran.append(1))
    assert cli.main(["watch"]) == 1
    assert ran == []   # the loop body never ran


def test_poll_prunes_the_archive_when_keep_days_is_set(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_ARCHIVE_KEEP_DAYS", "30")
    _poll_returning_one(monkeypatch)
    monkeypatch.setattr(cli, "group_stories", lambda arts, *, threshold: ())
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: ())
    pruned = _record_prune_calls(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--to", "you@example.com"]) == 0
    assert pruned == [30]


def test_poll_does_not_prune_the_archive_by_default(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_ARCHIVE_KEEP_DAYS", raising=False)
    _poll_returning_one(monkeypatch)
    monkeypatch.setattr(cli, "group_stories", lambda arts, *, threshold: ())
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: ())
    pruned = _record_prune_calls(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--to", "you@example.com"]) == 0
    assert pruned == []   # the archive keeps everything unless the user opts in


def test_poll_survives_a_prune_failure_after_delivery(monkeypatch, tmp_path, capsys):
    # Retention runs after the digest is delivered and the watermark written; an I/O error
    # deleting an old file is reported but must not fail the already-delivered poll.
    from newswatcher.errors import ArchiveError
    from newswatcher.store import FileStore
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_ARCHIVE_KEEP_DAYS", "30")
    _poll_returning_one(monkeypatch)
    monkeypatch.setattr(cli, "group_stories", lambda arts, *, threshold: ())
    monkeypatch.setattr(cli, "send_digest", lambda *a, **k: ())

    def _boom(self, keep_days):
        raise ArchiveError("cannot delete")

    monkeypatch.setattr(FileStore, "prune_older_than", _boom)
    assert cli.main(["poll", "--no-heal", "--to", "you@example.com"]) == 0
    assert "prune failed" in capsys.readouterr().err


def test_poll_rejects_a_nonnumeric_archive_keep_days(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_ARCHIVE_KEEP_DAYS", "forever")
    _poll_returning_one(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert "NEWSWATCHER_ARCHIVE_KEEP_DAYS" in capsys.readouterr().err


def test_poll_rejects_a_non_positive_archive_keep_days(monkeypatch, tmp_path, capsys):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_ARCHIVE_KEEP_DAYS", "0")
    _poll_returning_one(monkeypatch)
    assert cli.main(["poll", "--no-heal", "--no-store", "--to", "you@example.com"]) == 1
    assert "NEWSWATCHER_ARCHIVE_KEEP_DAYS" in capsys.readouterr().err


def test_poll_skips_when_another_is_running(monkeypatch, tmp_path, capsys):
    from newswatcher.lock import single_instance
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
    from newswatcher.poll import PollReport
    from newswatcher.summarize import Summary
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
    monkeypatch.delenv("NEWSWATCHER_LLM_PROVIDER", raising=False)
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store",
                     "--provider", "openai", "--model", "gpt-x"]) == 0
    assert captured == {"provider": "openai", "model": "gpt-x"}


def test_poll_provider_comes_from_environment_variable(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_LLM_PROVIDER", "claude")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    assert captured["provider"] == "claude"


def test_poll_model_comes_from_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("NEWSWATCHER_LLM_MODEL", "configured-model")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    assert captured["model"] == "configured-model"


def test_poll_empty_provider_flag_falls_through_to_setting(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.setenv("NEWSWATCHER_LLM_PROVIDER", "claude")
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store", "--provider", ""]) == 0
    assert captured["provider"] == "claude"


def test_poll_defaults_to_gemini(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("NEWSWATCHER_LLM_MODEL", raising=False)
    captured = _capture_provider(monkeypatch)
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store"]) == 0
    from newswatcher._llm import DEFAULT_PROVIDER
    assert captured["provider"] == DEFAULT_PROVIDER
    assert captured["model"] is None


def test_poll_unknown_provider_is_rejected(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_LLM_PROVIDER", raising=False)
    # a typo'd provider fails fast with a one-line error, even with nothing to summarize
    assert cli.main(["poll", "--no-mail", "--no-heal", "--no-store",
                     "--provider", "gemninni"]) == 1


def test_heal_threads_provider_to_heal_source(monkeypatch, tmp_path):
    _xdg(monkeypatch, tmp_path)
    monkeypatch.delenv("NEWSWATCHER_LLM_PROVIDER", raising=False)
    from newswatcher.sources import Source
    captured = {}

    def fake_heal_source(source, *, gate, should_apply, provider, model, **kwargs):
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


# --- schedule: the subcommand had no test, so only the live round-trip ever checked it ---

def _fake_cron(monkeypatch, initial=()):
    """Pin the POSIX backend and give it an in-memory crontab, so these exercise the real
    _run_schedule and the real install/remove/status rather than a stubbed CLI."""
    from newswatcher import schedule
    store = {"lines": list(initial)}
    monkeypatch.setattr(schedule, "_is_windows", lambda: False)
    monkeypatch.setattr(schedule, "_read_crontab", lambda: list(store["lines"]))
    monkeypatch.setattr(schedule, "_write_crontab",
                        lambda lines: store.__setitem__("lines", list(lines)))
    return store


def test_schedule_install_uses_the_given_interval(monkeypatch, capsys):
    _fake_cron(monkeypatch)
    assert cli.main(["schedule", "install", "--every", "2h"]) == 0
    assert "installed: 0 */2 * * * " in capsys.readouterr().out


def test_schedule_install_defaults_the_interval(monkeypatch, capsys):
    from newswatcher.schedule import DEFAULT_INTERVAL_MINUTES
    _fake_cron(monkeypatch)
    assert cli.main(["schedule", "install"]) == 0
    assert f"*/{DEFAULT_INTERVAL_MINUTES} * * * * " in capsys.readouterr().out


def test_schedule_status_round_trips_install(monkeypatch, capsys):
    _fake_cron(monkeypatch)
    assert cli.main(["schedule", "status"]) == 0
    assert capsys.readouterr().out.strip() == "not installed"
    cli.main(["schedule", "install", "--every", "15"])
    capsys.readouterr()
    assert cli.main(["schedule", "status"]) == 0
    assert capsys.readouterr().out.startswith("*/15 * * * * ")


def test_schedule_remove_reports_both_outcomes(monkeypatch, capsys):
    _fake_cron(monkeypatch)
    assert cli.main(["schedule", "remove"]) == 0
    assert "no poll job was installed" in capsys.readouterr().out
    cli.main(["schedule", "install"])
    capsys.readouterr()
    assert cli.main(["schedule", "remove"]) == 0
    assert "removed the poll job" in capsys.readouterr().out


def test_schedule_install_rejects_a_bad_interval(monkeypatch, capsys):
    # _interval raises inside argparse, and main turns argparse's SystemExit into a code.
    _fake_cron(monkeypatch)
    assert cli.main(["schedule", "install", "--every", "soon"]) == 2
    assert "interval must be minutes" in capsys.readouterr().err


def test_watch_ends_on_a_corrupt_state_file(monkeypatch, tmp_path):
    # A corrupt state file is permanent-at-startup; the pre-flight read_state must end the
    # watch (exit 1) rather than let the loop spin on the ConfigError every tick.
    _xdg(monkeypatch, tmp_path)
    from newswatcher.state import state_path
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ not valid json", encoding="utf-8")
    ran = []
    monkeypatch.setattr(cli, "_run_poll", lambda a: ran.append(1))
    assert cli.main(["watch"]) == 1
    assert ran == []   # ended before the loop body ever ran
