from newswatcher.lock import single_instance


def _state_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("NEWSWATCHER_STATE_DIR", raising=False)


def test_single_instance_acquires_when_free(monkeypatch, tmp_path):
    _state_home(monkeypatch, tmp_path)
    with single_instance("poll") as acquired:
        assert acquired is True


def test_second_holder_is_refused_then_released(monkeypatch, tmp_path):
    _state_home(monkeypatch, tmp_path)
    with single_instance("poll") as first:
        assert first is True
        with single_instance("poll") as second:
            assert second is False   # another holder already has it
    # released on exit, so a later run acquires again
    with single_instance("poll") as again:
        assert again is True


class _FakeMsvcrt:
    """Simulate OS-level exclusion: the first LK_NBLCK wins, a second raises until unlocked."""
    LK_NBLCK = 1
    LK_UNLCK = 2

    def __init__(self):
        self.held = False

    def locking(self, fd, mode, nbytes):
        if mode == self.LK_NBLCK:
            if self.held:
                raise OSError("locked")
            self.held = True
        elif mode == self.LK_UNLCK:
            self.held = False


def test_windows_lock_acquires_and_refuses_then_releases(monkeypatch, tmp_path):
    import newswatcher.lock as lock
    _state_home(monkeypatch, tmp_path)
    monkeypatch.setattr(lock, "_is_windows", lambda: True)
    monkeypatch.setattr(lock, "msvcrt", _FakeMsvcrt())
    with single_instance("poll") as first:
        assert first is True
        with single_instance("poll") as second:
            assert second is False   # msvcrt region lock excludes the second holder
    with single_instance("poll") as again:
        assert again is True         # released on exit


def test_no_backend_degrades_to_always_acquire(monkeypatch, tmp_path):
    import newswatcher.lock as lock
    _state_home(monkeypatch, tmp_path)
    monkeypatch.setattr(lock, "_is_windows", lambda: False)
    monkeypatch.setattr(lock, "fcntl", None)
    monkeypatch.setattr(lock, "msvcrt", None)
    with single_instance("poll") as acquired:
        assert acquired is True   # no advisory lock available anywhere
