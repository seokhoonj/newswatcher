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
        ScheduleError: no ``crontab`` command is available, or the crontab could not be
            read or written.
    """
    line = f"*/{every_minutes} * * * * {' '.join(resolve_poll_command())} {_MARKER}"
    lines = [ln for ln in _read_crontab() if _MARKER not in ln]
    lines.append(line)
    _write_crontab(lines)
    return line


def remove_poll() -> bool:
    """Remove the newswatch poll line; return whether one was present."""
    current = _read_crontab()
    kept = [ln for ln in current if _MARKER not in ln]
    if len(kept) == len(current):
        return False
    _write_crontab(kept)
    return True


def poll_status() -> str | None:
    """The installed newswatch cron line, or None when not installed."""
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
