"""Suite-wide guards, so a test run cannot reach past the tmp_path it was given.

Both fixtures exist because a test escaped once. The scheduler backends shell out to the
host's real ``crontab`` / ``schtasks``, and a Windows run of the cron cases -- which faked
the crontab seams but not the platform seam -- registered a live scheduled task on the
developer's machine. The directory fixture closes the same class of hole on the other
side: ``state_dir()`` falls through the env var to ``config.toml``, so a developer who has
a real ``~/.config/newswatch/config.toml`` with a ``state_dir`` key would have the lock
tests take the real ``poll`` lock and silently starve their own scheduled poll.
"""

import pytest

from newswatch import schedule

_DIR_ENV = ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME")
_DIR_OVERRIDES = ("NEWSWATCH_DATA_DIR", "NEWSWATCH_STATE_DIR")


def _forbidden(kind: str):
    def deny() -> str:
        raise AssertionError(
            f"test reached the real {kind} binary; fake the scheduler seam instead of "
            f"editing this machine's schedule")
    return deny


@pytest.fixture(autouse=True)
def _no_real_scheduler(monkeypatch):
    monkeypatch.setattr(schedule, "_crontab_bin", _forbidden("crontab"))
    monkeypatch.setattr(schedule, "_schtasks_bin", _forbidden("schtasks"))


@pytest.fixture(autouse=True)
def _isolated_dirs(monkeypatch, tmp_path):
    """Point every config / data / state lookup at this test's tmp_path. A test that wants
    a specific layout still sets its own afterwards; this only ensures that forgetting to
    cannot reach the developer's real directories."""
    for name in _DIR_ENV:
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    for name in _DIR_OVERRIDES:
        monkeypatch.delenv(name, raising=False)
