import pytest

from newswatcher import schedule
from newswatcher.errors import ScheduleError
from newswatcher.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    install_poll,
    parse_interval,
    poll_status,
    remove_poll,
)


def _fake_crontab(monkeypatch, initial=()):
    """Replace the crontab read/write seams with an in-memory list, and pin the backend to
    POSIX. Without the pin these cases dispatch to schtasks when the suite runs on Windows
    -- which both fails the cron assertions and edits the real Task Scheduler."""
    store = {"lines": list(initial)}
    monkeypatch.setattr(schedule, "_is_windows", lambda: False)
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


def test_cron_line_does_not_over_quote_a_space_free_command(monkeypatch):
    _fake_crontab(monkeypatch)
    monkeypatch.setattr(schedule, "resolve_poll_command",
                        lambda: ["/usr/bin/python3", "-m", "newswatcher", "poll"])
    assert "/usr/bin/python3 -m newswatcher poll" in install_poll(30)   # no needless quotes


def test_cron_line_quotes_a_command_path_with_spaces(monkeypatch):
    _fake_crontab(monkeypatch)
    monkeypatch.setattr(schedule, "resolve_poll_command",
                        lambda: ["/opt/py 3/bin/python", "-m", "newswatcher", "poll"])
    line = install_poll(30)
    assert "'/opt/py 3/bin/python'" in line   # quoted so the space cannot split the crontab line


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
    from newswatcher.schedule import _MARKER
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


# --- Windows (schtasks) backend: unit-tested via the _is_windows seam + a fake _schtasks ---

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2"><Triggers><TimeTrigger>
<StartBoundary>2026-09-01T12:03:00</StartBoundary>
<Repetition><Interval>PT45M</Interval></Repetition>
</TimeTrigger></Triggers></Task>"""


def _fake_schtasks(monkeypatch, calls, *, query_found=False, stdout=_TASK_XML):
    """Record schtasks arg lists; return a CompletedProcess-like object."""
    import subprocess

    def fake(*args, check=True):
        calls.append(list(args))
        rc = 0 if (query_found or "/Query" not in args) else 1
        return subprocess.CompletedProcess(args, rc, stdout=stdout if query_found else "",
                                           stderr="")

    monkeypatch.setattr(schedule, "_schtasks", fake)


def test_windows_install_minute_interval(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls)
    schedule.install_poll(45)   # cron rejects 45; Windows accepts it
    args = calls[0]
    assert args[:4] == ["/Create", "/F", "/TN", schedule._TASK_NAME]
    assert args[args.index("/SC") + 1] == "MINUTE"
    assert args[args.index("/MO") + 1] == "45"


def test_windows_install_daily_interval(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls)
    schedule.install_poll(2880)   # 2 days
    args = calls[0]
    assert args[args.index("/SC") + 1] == "DAILY"
    assert args[args.index("/MO") + 1] == "2"


def test_windows_install_rejects_over_cap_non_daily(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    _fake_schtasks(monkeypatch, [])
    with pytest.raises(ScheduleError):
        schedule.install_poll(1500)   # 25h: over the MINUTE cap, not a whole day


def test_windows_install_quotes_the_command(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    monkeypatch.setattr(schedule, "resolve_poll_command",
                        lambda: [r"C:\Program Files\Py\python.exe", "-m", "newswatcher", "poll"])
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls)
    schedule.install_poll(30)
    tr = calls[0][calls[0].index("/TR") + 1]
    assert tr.startswith('"C:\\Program Files\\Py\\python.exe"')   # exe with spaces is quoted
    assert "newswatcher" in tr and "poll" in tr


def test_windows_status_and_remove_when_present(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls, query_found=True)
    assert schedule.poll_status() is not None       # /Query found the task
    assert schedule.remove_poll() is True           # present -> deleted
    assert any("/Delete" in c for c in calls)


def test_windows_status_reports_the_interval(monkeypatch):
    # The default schtasks table gives a localized next-run time and state and no interval
    # at all, so a 45-minute poll and a 30-minute one printed the same line. Status must
    # report back what install printed, the way the crontab backend does.
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls, query_found=True)
    assert schedule.poll_status() == f"{schedule._TASK_NAME}: /SC MINUTE /MO 45"
    assert "/XML" in calls[0]   # the only locale-independent view schtasks offers


def test_windows_status_reports_a_daily_interval(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    daily = ("<Task><Triggers><CalendarTrigger><ScheduleByDay><DaysInterval>2"
             "</DaysInterval></ScheduleByDay></CalendarTrigger></Triggers></Task>")
    _fake_schtasks(monkeypatch, [], query_found=True, stdout=daily)
    assert schedule.poll_status() == f"{schedule._TASK_NAME}: /SC DAILY /MO 2"


def test_windows_status_survives_a_hand_edited_task(monkeypatch):
    # Someone may have changed the trigger in Task Scheduler; status must still report the
    # task as present rather than crash or claim it is absent.
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    _fake_schtasks(monkeypatch, [], query_found=True, stdout="<Task><Triggers/></Task>")
    status = schedule.poll_status()
    assert status is not None and schedule._TASK_NAME in status


def test_windows_remove_when_absent(monkeypatch):
    monkeypatch.setattr(schedule, "_is_windows", lambda: True)
    calls: list[list[str]] = []
    _fake_schtasks(monkeypatch, calls, query_found=False)
    assert schedule.poll_status() is None
    assert schedule.remove_poll() is False          # nothing to delete
    assert not any("/Delete" in c for c in calls)


# --- schtasks output decoding: the console codepage is not the locale encoding -----------

def test_schtasks_decodes_with_the_console_encoding(monkeypatch):
    """The fix is a pair of kwargs on the subprocess call, and every other Windows case
    fakes _schtasks itself -- one level above this body. Without this test the encoding
    could be dropped and the whole suite would stay green while `schedule status` died on
    a console whose codepage differs from the locale's."""
    import subprocess as real_subprocess
    seen: dict[str, object] = {}

    class _Recorder:
        @staticmethod
        def run(argv, **kwargs):
            seen.update(kwargs)
            return real_subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(schedule, "_schtasks_bin", lambda: "schtasks.exe")
    monkeypatch.setattr(schedule, "subprocess", _Recorder)
    schedule._schtasks("/Query")
    assert seen["encoding"] == schedule._console_encoding()
    assert seen["errors"] == "replace"
    assert "text" not in seen   # text=True is what decoded with the locale encoding



def test_console_encoding_prefers_the_console_codepage(monkeypatch):
    monkeypatch.setattr(schedule, "_console_codepage", lambda: 949)
    assert schedule._console_encoding() == "cp949"


def test_console_encoding_maps_utf8_codepage(monkeypatch):
    # A Korean-locale machine running chcp 65001: decoding as cp949 used to raise inside
    # subprocess's reader thread, drop stdout, and crash poll_status with AttributeError.
    monkeypatch.setattr(schedule, "_console_codepage", lambda: 65001)
    assert schedule._console_encoding() == "utf-8"


def test_console_encoding_uses_the_oem_codepage_without_a_console(monkeypatch):
    # A console-less parent's console-app child gets a fresh console at the OEM codepage.
    # The locale encoding is the ANSI one -- a different axis, and UTF-8 mode redefines it
    # without changing a byte of what schtasks emits.
    monkeypatch.setattr(schedule, "_console_codepage", lambda: 0)
    monkeypatch.setattr(schedule, "_oem_codepage", lambda: 437)
    assert schedule._console_encoding() == "cp437"


def test_console_encoding_falls_back_when_neither_answers(monkeypatch):
    import locale
    monkeypatch.setattr(schedule, "_console_codepage", lambda: 0)
    monkeypatch.setattr(schedule, "_oem_codepage", lambda: 0)
    assert schedule._console_encoding() == locale.getpreferredencoding(False)


def test_console_encoding_falls_back_on_unknown_codepage(monkeypatch):
    import locale
    monkeypatch.setattr(schedule, "_console_codepage", lambda: 99999)   # no Python codec
    monkeypatch.setattr(schedule, "_oem_codepage", lambda: 0)
    assert schedule._console_encoding() == locale.getpreferredencoding(False)


def test_codepage_is_zero_off_windows(monkeypatch):
    # ctypes.windll exists only on Windows; asking elsewhere must degrade, not raise.
    import ctypes
    monkeypatch.delattr(ctypes, "windll", raising=False)
    assert schedule._console_codepage() == 0
    assert schedule._oem_codepage() == 0


def test_run_converts_subprocess_launch_failure_to_scheduleerror(monkeypatch):
    def boom(*a, **k):
        raise OSError("exec failed")
    monkeypatch.setattr("newswatcher.schedule.subprocess.run", boom)
    with pytest.raises(ScheduleError):
        schedule._run(["crontab", "-l"])


def test_run_converts_timeout_to_scheduleerror(monkeypatch):
    import subprocess as _sp

    def hang(*a, **k):
        raise _sp.TimeoutExpired(cmd="crontab", timeout=1)
    monkeypatch.setattr("newswatcher.schedule.subprocess.run", hang)
    with pytest.raises(ScheduleError):
        schedule._run(["crontab", "-l"])
