from newswatch.lock import single_instance


def _state_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.delenv("NEWSWATCH_STATE_DIR", raising=False)


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
