"""A best-effort single-instance lock so two polls do not run at once.

Overlapping polls -- a cron poll and a manual one, or two crons -- would double-spend
the LLM, mail duplicate digests, and race on the state watermark. ``single_instance``
holds an exclusive advisory lock on a file in ``state_dir()`` for the duration of a
block and yields whether it was acquired, so the caller can skip a run already in
progress rather than pile on. Built on ``fcntl.flock`` (POSIX) and ``msvcrt.locking``
(Windows) -- both of which the OS releases automatically when the process exits, even on
a crash, so there is no stale lock to clean up. On a platform with neither it is a no-op
that always acquires."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from newswatcher.config import state_dir

try:
    import fcntl
except ImportError:   # non-POSIX
    fcntl = None      # type: ignore[assignment]

try:
    import msvcrt
except ImportError:   # non-Windows
    msvcrt = None     # type: ignore[assignment]

__all__ = ["single_instance"]


def _is_windows() -> bool:
    return os.name == "nt"


@contextmanager
def single_instance(name: str) -> Iterator[bool]:
    """Hold an exclusive lock named ``name`` for the block. Yields True when the lock was
    acquired, False when another process already holds it (the caller should then skip its
    run). Uses ``fcntl.flock`` on POSIX and ``msvcrt.locking`` (a byte-range lock) on
    Windows; a platform with neither is a no-op that always yields True.

    Raises:
        ConfigError: no state directory can be resolved (propagated from ``state_dir``).
    """
    path = state_dir() / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    if _is_windows() and msvcrt is not None:
        # Open without truncating so a concurrent holder's region lock is undisturbed.
        with path.open("a+") as handle:
            handle.seek(0)
            try:
                # msvcrt is win32-only, so its symbols are invisible to mypy on this platform.
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            except OSError:
                yield False   # another holder has the region
                return
            try:
                yield True
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    if fcntl is not None:
        with path.open("w") as handle:
            try:
                # fcntl is POSIX-only, so its symbols are invisible to mypy on Windows.
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
            except OSError:
                yield False   # another holder has it; do not block
                return
            try:
                yield True
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)  # type: ignore[attr-defined]
        return
    yield True   # no advisory file lock available on this platform
