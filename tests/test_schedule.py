import pytest

from newswatch import schedule
from newswatch.errors import ScheduleError
from newswatch.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    install_poll,
    parse_interval,
)


def _fake_crontab(monkeypatch, initial=()):
    """Replace the crontab read/write seams with an in-memory list."""
    store = {"lines": list(initial)}
    monkeypatch.setattr(schedule, "_read_crontab", lambda: list(store["lines"]))
    monkeypatch.setattr(schedule, "_write_crontab",
                        lambda lines: store.__setitem__("lines", list(lines)))
    return store


def test_parse_interval_accepts_plain_minutes():
    assert parse_interval("15") == 15
    assert parse_interval("30m") == 30
    assert parse_interval("1h") == 60


def test_parse_interval_rejects_zero_and_garbage():
    with pytest.raises(ScheduleError):
        parse_interval("0")
    with pytest.raises(ScheduleError):
        parse_interval("soon")


def test_default_interval_is_positive():
    assert DEFAULT_INTERVAL_MINUTES >= 1


def test_install_sub_hour_uses_minute_step(monkeypatch):
    _fake_crontab(monkeypatch)
    assert install_poll(30).startswith("*/30 * * * * ")


def test_install_multi_hour_is_not_hourly(monkeypatch):
    # The bug: */120 in the minute field fires at minute 0 hourly, not every 2h.
    _fake_crontab(monkeypatch)
    line = install_poll(120)
    assert line.startswith("0 */2 * * * ")
    assert not line.startswith("*/120")


def test_install_hourly(monkeypatch):
    _fake_crontab(monkeypatch)
    assert install_poll(60).startswith("0 */1 * * * ")


def test_install_daily(monkeypatch):
    _fake_crontab(monkeypatch)
    assert install_poll(1440).startswith("0 0 */1 * * ")


def test_install_rejects_non_representable_interval(monkeypatch):
    _fake_crontab(monkeypatch)
    with pytest.raises(ScheduleError):
        install_poll(90)     # 1.5h -- not a simple cron step
    with pytest.raises(ScheduleError):
        install_poll(1500)   # 25h -- not a simple cron step
