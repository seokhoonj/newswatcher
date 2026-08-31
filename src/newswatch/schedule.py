"""Register the recurring poll with the user's crontab.

newswatch manages exactly one crontab line, tagged with a marker comment, so
installing or removing it never disturbs the user's other cron jobs. Interval parsing
accepts plain minutes (``15``), ``Nm``, or ``Nh``."""

from __future__ import annotations

import shutil
import subprocess
import sys

from newswatch.errors import ScheduleError

__all__ = [
    "DEFAULT_INTERVAL_MINUTES", "parse_interval", "resolve_poll_command",
    "install_poll", "remove_poll", "poll_status",
]

DEFAULT_INTERVAL_MINUTES = 30
_MARKER = "# newswatch-poll"


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
    """Install (or replace) the newswatch poll crontab line at ``every_minutes``; return
    the installed cron line.

    Raises:
        ScheduleError: the interval is not expressible as a simple cron step, no
            ``crontab`` command is available, or the crontab could not be read or
            written.
    """
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


def remove_poll() -> bool:
    """Remove the newswatch poll line; return whether one was present.

    Raises:
        ScheduleError: no ``crontab`` command is available, or the crontab could not be
            read or written.
    """
    current = _read_crontab()
    kept = [ln for ln in current if _MARKER not in ln]
    if len(kept) == len(current):
        return False
    _write_crontab(kept)
    return True


def poll_status() -> str | None:
    """The installed newswatch cron line, or None when not installed.

    Raises:
        ScheduleError: no ``crontab`` command is available, or the crontab could not be
            read.
    """
    for line in _read_crontab():
        if _MARKER in line:
            return line
    return None


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
