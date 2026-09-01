"""Atomic file writes: temp file in the target directory, then rename over the
target, so a crash or a concurrent reader never sees a half-written file, and two
overlapping writers do not share a temp path."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

__all__ = ["write_text_atomic", "write_bytes_atomic"]


def write_text_atomic(path: Path, text: str, error_cls: type[Exception]) -> None:
    """Write ``text`` to ``path`` atomically; wrap any I/O failure in ``error_cls``."""
    write_bytes_atomic(path, text.encode("utf-8"), error_cls)


def write_bytes_atomic(path: Path, data: bytes, error_cls: type[Exception]) -> None:
    """Write ``data`` to ``path`` atomically; wrap any I/O failure in ``error_cls``."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())   # flush to disk before the rename, so a crash
                                            # after os.replace cannot leave a half-written file
            os.replace(tmp, path)
        except OSError:
            tmp.unlink(missing_ok=True)
            raise
    except OSError as err:
        raise error_cls(f"could not write {path}: {err}") from err
