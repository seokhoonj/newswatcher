import pytest

from newswatch import schedule
from newswatch.errors import ScheduleError
from newswatch.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    install_poll,
    parse_interval,
    poll_status,
    remove_poll,
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


def test_install_twelve_hour_divisor(monkeypatch):
    _fake_crontab(monkeypatch)
    assert install_poll(480).startswith("0 */8 * * * ")   # 8h divides 24


def test_install_rejects_zero_without_crashing(monkeypatch):
    # install_poll is public; a 0 must raise the domain error, not ZeroDivisionError
    # from the 60 % every_minutes divisor check.
    _fake_crontab(monkeypatch)
    with pytest.raises(ScheduleError):
        install_poll(0)


def test_install_rejects_non_divisor_intervals(monkeypatch):
    # A cron */step restarts at the field's zero each hour/day, so a non-divisor
    # mis-fires: */45 fires :00,:45 (45-then-15); 0 */5 fires h0,5,10,15,20 then a 4h gap.
    _fake_crontab(monkeypatch)
    with pytest.raises(ScheduleError):
        install_poll(45)     # does not divide 60 minutes
    with pytest.raises(ScheduleError):
        install_poll(300)    # 5h -- does not divide 24 hours
    with pytest.raises(ScheduleError):
        install_poll(2880)   # 2 days -- day-of-month stepping is irregular across months


def _marker_lines(store):
    from newswatch.schedule import _MARKER
    return [ln for ln in store["lines"] if _MARKER in ln]


def test_install_replaces_existing_not_duplicate(monkeypatch):
    store = _fake_crontab(monkeypatch)
    install_poll(30)
    install_poll(60)
    assert len(_marker_lines(store)) == 1                 # one poll line, not two
    assert _marker_lines(store)[0].startswith("0 */1 * * * ")   # the latest interval


def test_install_keeps_other_lines(monkeypatch):
    store = _fake_crontab(monkeypatch, ["0 3 * * * /usr/bin/backup"])
    install_poll(30)
    assert "0 3 * * * /usr/bin/backup" in store["lines"]   # unrelated job untouched


def test_remove_absent_reports_false(monkeypatch):
    _fake_crontab(monkeypatch, ["0 3 * * * /usr/bin/backup"])
    assert remove_poll() is False


def test_remove_present_reports_true_and_keeps_others(monkeypatch):
    store = _fake_crontab(monkeypatch, ["0 3 * * * /usr/bin/backup"])
    install_poll(30)
    assert remove_poll() is True
    assert _marker_lines(store) == []
    assert "0 3 * * * /usr/bin/backup" in store["lines"]


def test_status_reports_installed_line(monkeypatch):
    _fake_crontab(monkeypatch)
    assert poll_status() is None
    line = install_poll(30)
    assert poll_status() == line
