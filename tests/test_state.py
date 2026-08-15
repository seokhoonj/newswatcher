from newswatch.feed import FeedItem
from newswatch.state import State, read_state, write_state


def _item(guid, published=""):
    return FeedItem(title="t", link=guid, guid=guid, published=published, source_name="s")


def test_is_new_then_mark_seen(tmp_path):
    st = State()
    it = _item("g1", "2026-08-15T00:00:00Z")
    assert st.is_new("s", it) is True
    st.mark_seen("s", it)
    assert st.is_new("s", it) is False


def test_newer_published_is_new_even_if_guid_differs(tmp_path):
    st = State()
    st.mark_seen("s", _item("g1", "2026-08-15T00:00:00Z"))
    assert st.is_new("s", _item("g2", "2026-08-16T00:00:00Z")) is True
    assert st.is_new("s", _item("g3", "2026-08-14T00:00:00Z")) is False


def test_empty_poll_counter(tmp_path):
    st = State()
    assert st.note_empty("s") == 1
    assert st.note_empty("s") == 2
    st.clear_empty("s")
    assert st.note_empty("s") == 1


def test_roundtrip_persists(tmp_path):
    path = tmp_path / "state.json"
    st = State()
    st.mark_seen("s", _item("g1", "2026-08-15T00:00:00Z"))
    st.note_empty("s")
    write_state(st, path)
    back = read_state(path)
    assert back.is_new("s", _item("g1", "2026-08-15T00:00:00Z")) is False
    assert back.empty_polls_by_source["s"] == 1
