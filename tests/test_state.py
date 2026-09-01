from newswatcher.feed import FeedItem
from newswatcher.state import _SEEN_CAP, State, read_state, write_state


def _item(guid, published=""):
    return FeedItem(title="t", link=guid, guid=guid, published=published, source_name="s")


def test_is_new_then_mark_seen(tmp_path):
    st = State()
    it = _item("g1", "2026-08-15T00:00:00Z")
    assert st.is_new("s", it) is True
    st.mark_seen("s", it)
    assert st.is_new("s", it) is False


def test_seen_is_per_source(tmp_path):
    st = State()
    st.mark_seen("a", _item("g1"))
    assert st.is_new("a", _item("g1")) is False
    assert st.is_new("b", _item("g1")) is True


def test_same_timestamp_items_do_not_ping_pong(tmp_path):
    # Two items sharing the newest published time: once both are marked, NEITHER
    # is offered again (the old single-slot watermark ping-ponged and re-collected
    # both every poll).
    st = State()
    a = _item("gA", "2026-08-15T00:00:00Z")
    b = _item("gB", "2026-08-15T00:00:00Z")
    st.mark_seen("s", a)
    st.mark_seen("s", b)
    assert st.is_new("s", a) is False
    assert st.is_new("s", b) is False


def test_no_date_items_are_deduped_individually(tmp_path):
    # A crawl source with no date selector yields published="" for every row. Each
    # distinct guid must be remembered on its own (the old watermark re-collected the
    # whole listing every poll).
    st = State()
    rows = [_item(f"g{i}") for i in range(5)]
    for row in rows:
        assert st.is_new("s", row) is True
        st.mark_seen("s", row)
    for row in rows:
        assert st.is_new("s", row) is False


def test_older_unseen_item_is_new(tmp_path):
    # Behavior change vs the old published-watermark: an unseen article is new even
    # when its published time is older than something already seen. Dedup is by guid,
    # so an out-of-order publish is collected rather than silently dropped.
    st = State()
    st.mark_seen("s", _item("g1", "2026-08-15T00:00:00Z"))
    assert st.is_new("s", _item("g2", "2026-08-14T00:00:00Z")) is True


def test_seen_set_is_bounded(tmp_path):
    # The recently-seen set is capped so it cannot grow without bound; the oldest
    # guids are evicted first and may re-collect once.
    st = State()
    for i in range(_SEEN_CAP + 10):
        st.mark_seen("s", _item(f"g{i}"))
    assert st.is_new("s", _item("g0")) is True                 # evicted (oldest)
    assert st.is_new("s", _item(f"g{_SEEN_CAP + 9}")) is False  # newest retained
    assert len(st.seen_guids_by_source["s"]) == _SEEN_CAP


def test_evicted_guid_relisted_is_recollected_then_reseen(tmp_path):
    # After eviction a re-listed guid collects once more; marking it seen again keeps the
    # cap and evicts the next-oldest -- the full evict/relist/re-mark lifecycle.
    st = State()
    for i in range(_SEEN_CAP + 10):
        st.mark_seen("s", _item(f"g{i}"))
    assert st.is_new("s", _item("g0")) is True      # g0 was evicted -> collectable again
    st.mark_seen("s", _item("g0"))                  # re-collected
    assert st.is_new("s", _item("g0")) is False     # now seen again
    assert len(st.seen_guids_by_source["s"]) == _SEEN_CAP
    assert st.is_new("s", _item("g10")) is True     # marking g0 evicted the next-oldest


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
    st.mark_seen("s", _item("g2"))
    st.note_empty("s")
    write_state(st, path)
    back = read_state(path)
    assert back.is_new("s", _item("g1", "2026-08-15T00:00:00Z")) is False
    assert back.is_new("s", _item("g2")) is False
    assert back.is_new("s", _item("g3")) is True
    assert back.empty_polls_by_source["s"] == 1


def test_read_state_raises_on_a_corrupt_file(tmp_path):
    # A corrupt state file must raise, not read as empty -- else the poll's write-back would
    # wipe every source's watermark (mass re-collect and re-send).
    import pytest

    from newswatcher.errors import ConfigError
    p = tmp_path / "state.json"
    p.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(ConfigError):
        read_state(p)
