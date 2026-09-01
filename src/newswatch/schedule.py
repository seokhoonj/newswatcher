"""Register the recurring poll with the OS scheduler: crontab on Linux/macOS, schtasks on
Windows.

On POSIX, newswatch manages exactly one crontab line tagged with a marker comment, so
installing or removing it never disturbs the user's other cron jobs. On Windows it manages
one scheduled task named ``newswatch-poll``. Interval parsing accepts plain minutes
(``15``), ``Nm``, or ``Nh``; which intervals are expressible differs by backend (see
``_cron_time_spec`` and ``_win_schedule``)."""

from __future__ import annotations

import codecs
import ctypes
import locale
import os
import re
import shutil
import subprocess
import sys

from newswatch.errors import ScheduleError

__all__ = [
    "DEFAULT_INTERVAL_MINUTES", "parse_interval", "resolve_poll_command",
    "install_poll", "remove_poll", "poll_status",
]

DEFAULT_INTERVAL_MINUTES = 30
_MARKER = "# newswatch-poll"      # POSIX crontab marker comment
_TASK_NAME = "newswatch-poll"     # Windows scheduled-task name (the schtasks marker)


def _is_windows() -> bool:
    return os.name == "nt"


def parse_interval(text: str) -> int:
    """Parse an interval into whole minutes. Accepts ``N`` (minutes), ``Nm``, or ``Nh``.

    Raises:
        ScheduleError: the value is not a positive whole number of minutes.
    """
    raw = text.strip().lower()
    try:
        if raw.endswith("h"):
            minutes = int(raw[:-1]) * 60
        elif raw.endswith("m"):
            minutes = int(raw[:-1])
        else:
            minutes = int(raw)
    except ValueError:
        raise ScheduleError(f"interval must be minutes, or Nm / Nh; got {text!r}") from None
    if minutes < 1:
        raise ScheduleError(f"interval must be at least 1 minute, got {minutes}")
    return minutes


def resolve_poll_command() -> list[str]:
    """The command cron runs each tick: this interpreter's ``python -m newswatch poll``."""
    return [sys.executable, "-m", "newswatch", "poll"]


def install_poll(every_minutes: int) -> str:
    """Install (or replace) the recurring newswatch poll at ``every_minutes``; return the
    installed schedule line. Uses crontab on Linux/macOS and schtasks on Windows.

    Raises:
        ScheduleError: the interval is not expressible on this platform's scheduler, the
            scheduler command is unavailable, or the schedule could not be read or written.
    """
    if _is_windows():
        return _win_install(every_minutes)
    return _cron_install(every_minutes)


def _cron_install(every_minutes: int) -> str:
    line = f"{_cron_time_spec(every_minutes)} {' '.join(resolve_poll_command())} {_MARKER}"
    lines = [ln for ln in _read_crontab() if _MARKER not in ln]
    lines.append(line)
    _write_crontab(lines)
    return line


def _cron_time_spec(every_minutes: int) -> str:
    """The 5-field cron time spec that fires every ``every_minutes`` at a *regular*
    cadence. A cron ``*/step`` restarts at its field's zero each hour (minute) or day
    (hour), so a step that does not divide its field mis-fires: ``*/45`` fires at :00 and
    :45 (a 45-then-15 cadence), ``0 */5`` fires at hours 0,5,10,15,20 then a 4h gap, and
    day-of-month stepping is irregular across months of differing length. Only an interval
    that divides evenly is regular, so accept a sub-hour interval dividing 60, a whole
    number of hours dividing 24, or exactly one day, and reject the rest rather than
    silently mis-schedule.

    Raises:
        ScheduleError: the interval does not map to a regular cron schedule.
    """
    if every_minutes < 1:
        raise ScheduleError(f"interval must be at least 1 minute, got {every_minutes}")
    if every_minutes < 60:
        if 60 % every_minutes:
            raise _irregular(every_minutes)
        return f"*/{every_minutes} * * * *"
    if every_minutes % 60 == 0:
        hours = every_minutes // 60
        if hours < 24:
            if 24 % hours:
                raise _irregular(every_minutes)
            return f"0 */{hours} * * *"
        if hours == 24:
            return "0 0 */1 * *"   # daily
    raise _irregular(every_minutes)


def _irregular(every_minutes: int) -> ScheduleError:
    return ScheduleError(
        f"interval of {every_minutes} minutes has no regular cron schedule; use a "
        f"sub-hour interval that divides 60 (e.g. 15, 20, 30), a whole number of hours "
        f"that divides 24 (e.g. 60, 120, 240, 480), or one day (1440)")


# --- Windows backend (schtasks) -----------------------------------------------

def _win_schedule(every_minutes: int) -> tuple[str, str]:
    """The schtasks ``(/SC, /MO)`` pair for ``every_minutes``. schtasks has no cron
    divisor restriction, but its fields still bound it: ``/SC MINUTE`` takes 1-1439 and
    ``/SC DAILY`` takes a whole number of days.

    Raises:
        ScheduleError: the interval is under a minute, or over 1439 minutes without being a
            whole number of days (schtasks cannot express it either).
    """
    if every_minutes < 1:
        raise ScheduleError(f"interval must be at least 1 minute, got {every_minutes}")
    if every_minutes < 1440:
        return "MINUTE", str(every_minutes)
    if every_minutes % 1440 == 0:
        return "DAILY", str(every_minutes // 1440)
    raise ScheduleError(
        f"interval of {every_minutes} minutes has no schtasks schedule; use under 1440 "
        f"minutes or a whole number of days")


def _win_install(every_minutes: int) -> str:
    sc, mo = _win_schedule(every_minutes)
    command = subprocess.list2cmdline(resolve_poll_command())   # Windows-safe quoting
    _schtasks("/Create", "/F", "/TN", _TASK_NAME, "/TR", command, "/SC", sc, "/MO", mo)
    return f"{_TASK_NAME}: /SC {sc} /MO {mo}"


def _schtasks_bin() -> str:
    found = shutil.which("schtasks")
    if found is None:
        raise ScheduleError("no 'schtasks' command on this system; cannot schedule the poll")
    return found


def _kernel32_codepage(func_name: str) -> int:
    """Call a kernel32 codepage getter, or 0 off Windows."""
    try:
        return int(getattr(ctypes.windll.kernel32, func_name)())   # type: ignore[attr-defined]
    except AttributeError:
        return 0   # ctypes.windll exists only on Windows


def _console_codepage() -> int:
    """The console output codepage. 0 when the process has no console to ask -- a
    scheduled task or a GUI parent has none, and the call reports that by returning 0
    rather than by raising."""
    return _kernel32_codepage("GetConsoleOutputCP")


def _oem_codepage() -> int:
    """The OEM codepage, which is what a console tool started by a console-less parent
    writes in: Windows gives such a child a freshly allocated console at the OEM default."""
    return _kernel32_codepage("GetOEMCP")


def _codec_for(codepage: int) -> str | None:
    """The Python codec name for a Windows codepage, or None for 0 or a codepage Python
    has no codec for (708, 1361, 54936 and friends)."""
    if not codepage:
        return None
    name = "utf-8" if codepage == 65001 else f"cp{codepage}"
    try:
        codecs.lookup(name)
    except LookupError:
        return None
    return name


def _console_encoding() -> str:
    """The encoding schtasks writes in. A console tool emits text in the *console output*
    codepage, which need not be Python's locale encoding: on a Korean-locale machine whose
    console is UTF-8 (``chcp 65001``), decoding as cp949 raises inside subprocess's reader
    thread, which drops the output entirely and leaves ``stdout`` None.

    Ask the OS in the order the child actually follows: this process's console if it has
    one, else the OEM codepage its fresh console will get. Only if neither answers does
    this fall back to Python's locale encoding, which is the ANSI codepage -- a different
    axis, and one that UTF-8 mode redefines without changing what schtasks emits."""
    for codepage in (_console_codepage(), _oem_codepage()):
        name = _codec_for(codepage)
        if name is not None:
            return name
    return locale.getpreferredencoding(False)


def _schtasks(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    # errors="replace" so a codepage the OS misreported degrades a character rather than
    # losing the whole run. What newswatch *parses* is ASCII -- the exit code, and the XML
    # element names below -- but the trailing columns and stderr are localized, so a wrong
    # codepage still shows the user mojibake instead of their own language.
    result = subprocess.run([_schtasks_bin(), *args], capture_output=True,
                            encoding=_console_encoding(), errors="replace")
    if check and result.returncode != 0:
        raise ScheduleError(f"could not run schtasks: {result.stderr.strip()}")
    return result


def remove_poll() -> bool:
    """Remove the newswatch poll job; return whether one was present. crontab on
    Linux/macOS, schtasks on Windows.

    Raises:
        ScheduleError: the scheduler command is unavailable or the change failed.
    """
    return _win_remove() if _is_windows() else _cron_remove()


def poll_status() -> str | None:
    """The installed newswatch poll schedule line, or None when not installed.

    Raises:
        ScheduleError: the scheduler command is unavailable or could not be queried.
    """
    return _win_status() if _is_windows() else _cron_status()


def _cron_remove() -> bool:
    current = _read_crontab()
    kept = [ln for ln in current if _MARKER not in ln]
    if len(kept) == len(current):
        return False
    _write_crontab(kept)
    return True


def _cron_status() -> str | None:
    for line in _read_crontab():
        if _MARKER in line:
            return line
    return None


def _win_status() -> str | None:
    result = _schtasks("/Query", "/TN", _TASK_NAME, "/XML", check=False)
    if result.returncode != 0:
        return None   # schtasks returns non-zero when the task does not exist
    return f"{_TASK_NAME}: {_win_schedule_from_xml(result.stdout)}"


_XML_MINUTES = re.compile(r"<Interval>PT(\d+)M</Interval>")
_XML_DAYS = re.compile(r"<DaysInterval>(\d+)</DaysInterval>")


def _win_schedule_from_xml(xml: str) -> str:
    """The ``/SC .. /MO ..`` summary of a task's XML, so status reports the line install
    printed -- the crontab backend likewise reports back the line it wrote.

    Task Scheduler XML is the only locale-independent view schtasks offers. Its default
    table gives a name truncated at 40 characters plus a *localized* next-run time and
    state, from which the interval cannot be recovered at all: a 45-minute poll and a
    30-minute one print the same thing."""
    minutes = _XML_MINUTES.search(xml)
    if minutes:
        return f"/SC MINUTE /MO {minutes.group(1)}"
    days = _XML_DAYS.search(xml)
    if days:
        return f"/SC DAILY /MO {days.group(1)}"
    return "on a schedule newswatch did not set"   # hand-edited in Task Scheduler


def _win_remove() -> bool:
    if _win_status() is None:
        return False
    _schtasks("/Delete", "/F", "/TN", _TASK_NAME)
    return True


def _crontab_bin() -> str:
    found = shutil.which("crontab")
    if found is None:
        raise ScheduleError("no 'crontab' command on this system; cannot schedule the poll")
    return found


def _read_crontab() -> list[str]:
    result = subprocess.run([_crontab_bin(), "-l"], capture_output=True, text=True)
    if result.returncode != 0 and "no crontab" not in result.stderr.lower():
        raise ScheduleError(f"could not read crontab: {result.stderr.strip()}")
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def _write_crontab(lines: list[str]) -> None:
    payload = "\n".join(lines) + "\n" if lines else ""
    result = subprocess.run([_crontab_bin(), "-"], input=payload, text=True,
                            capture_output=True)
    if result.returncode != 0:
        raise ScheduleError(f"could not write crontab: {result.stderr.strip()}")
