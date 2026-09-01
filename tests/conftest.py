"""Suite-wide guards.

The scheduler backends shell out to the host's real ``crontab`` / ``schtasks``, so a test
that reaches them edits the developer's own machine. Every scheduler test is meant to stop
at a fake seam; this makes the *unfaked* path fail loudly instead of silently installing a
job, which is how a Windows run of the cron cases once registered a live scheduled task.
"""

import pytest

from newswatch import schedule


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
