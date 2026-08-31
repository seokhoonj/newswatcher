"""A best-effort single-instance lock so two polls do not run at once.

Overlapping polls -- a cron poll and a manual one, or two crons -- would double-spend
the LLM, mail duplicate digests, and race on the state watermark. ``single_instance``
holds an exclusive advisory lock on a file in ``state_dir()`` for the duration of a
block and yields whether it was acquired, so the caller can skip a run already in
progress rather than pile on. Built on ``fcntl.flock`` (POSIX), which the kernel
releases automatically when the process exits -- even on a crash -- so there is no
stale lock to clean up. Where ``fcntl`` is unavailable (Windows), it is a no-op that
always acquires."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from newswatch.config import state_dir

try:
    import fcntl
except ImportError:   # non-POSIX (Windows): no advisory file lock available
    fcntl = None      # type: ignore[assignment]

__all__ = ["single_instance"]


@contextmanager
def single_instance(name: str) -> Iterator[bool]:
    """Hold an exclusive lock named ``name`` for the block. Yields True when the lock
    was acquired, False when another process already holds it (the caller should then
    skip its run). A no-op that always yields True where ``fcntl`` is unavailable.

    Raises:
        ConfigError: no state directory can be resolved (propagated from ``state_dir``).
    """
    if fcntl is None:
        yield True
        return
    path = state_dir() / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False   # another holder has it; do not block
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
