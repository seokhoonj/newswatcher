import os

import pytest

from newswatcher._atomic import write_bytes_atomic, write_text_atomic


class _WriteError(Exception):
    pass


def test_write_bytes_atomic_round_trip(tmp_path):
    target = tmp_path / "sub" / "data.bin"
    write_bytes_atomic(target, b"payload", _WriteError)
    assert target.read_bytes() == b"payload"


def test_write_text_atomic_round_trip(tmp_path):
    target = tmp_path / "data.txt"
    write_text_atomic(target, "hello", _WriteError)
    assert target.read_text(encoding="utf-8") == "hello"


def test_write_bytes_atomic_failure_preserves_target_and_removes_tmp(tmp_path, monkeypatch):
    # A write that fails midway (here fsync raises) must wrap the error, leave the previous
    # contents intact, and not litter the directory with the half-written temp file.
    target = tmp_path / "data.bin"
    target.write_bytes(b"original")

    def boom(_fd):
        raise OSError("disk full")

    monkeypatch.setattr("newswatcher._atomic.os.fsync", boom)
    with pytest.raises(_WriteError):
        write_bytes_atomic(target, b"replacement", _WriteError)
    assert target.read_bytes() == b"original"
    assert [p.name for p in tmp_path.iterdir() if p.name != "data.bin"] == []
    assert not any(p.suffix == ".tmp" for p in tmp_path.iterdir())


def test_write_bytes_atomic_wraps_a_bad_directory(tmp_path):
    # The target's parent is a file, so mkdir/mkstemp fails -- the error must surface as the
    # caller's error class, not a bare OSError.
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"x")
    target = blocker / "data.bin"
    with pytest.raises(_WriteError):
        write_bytes_atomic(target, b"payload", _WriteError)
    assert os.path.isfile(blocker)


def test_write_text_atomic_wraps_an_encode_failure(tmp_path):
    # A lone surrogate cannot be UTF-8 encoded; the wrap surfaces it as the caller's
    # error class (chained) rather than a bare UnicodeEncodeError escaping past the caller.
    with pytest.raises(_WriteError) as excinfo:
        write_text_atomic(tmp_path / "x.txt", "\ud800", _WriteError)
    assert isinstance(excinfo.value.__cause__, UnicodeEncodeError)
    assert not list(tmp_path.glob("*"))   # nothing half-written
