import pytest
from tomlite import TOMLEditor

from newswatcher import _toml


class _Err(Exception):
    pass


def test_read_table_array_returns_entries(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('[[item]]\nname = "a"\n\n[[item]]\nname = "b"\n', encoding="utf-8")
    assert _toml.read_table_array(path, "item", _Err) == [{"name": "a"}, {"name": "b"}]


def test_read_table_array_missing_key_is_empty(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('other = 1\n', encoding="utf-8")
    assert _toml.read_table_array(path, "item", _Err) == []


def test_read_table_array_scalar_key_raises(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('item = "scalar"\n', encoding="utf-8")
    with pytest.raises(_Err):
        _toml.read_table_array(path, "item", _Err)


def test_read_table_array_non_utf8_raises(tmp_path):
    path = tmp_path / "x.toml"
    path.write_bytes(b"\xff\xfe not utf-8")
    with pytest.raises(_Err):
        _toml.read_table_array(path, "item", _Err)


def test_append_entry_creates_the_file(tmp_path):
    path = tmp_path / "x.toml"
    _toml.append_entry(path, "item", [("name", "보험"), ("words", ("a", "b"))], _Err)
    # non-ASCII is kept verbatim and a string tuple renders as an inline array
    assert path.read_text(encoding="utf-8") == '[[item]]\nname = "보험"\nwords = ["a", "b"]\n'


def test_append_entry_leaves_existing_blocks_and_comments_intact(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('# hand-written note\n[[item]]\nname = "a"\n', encoding="utf-8")
    _toml.append_entry(path, "item", [("name", "b")], _Err)
    text = path.read_text(encoding="utf-8")
    assert text.startswith('# hand-written note\n[[item]]\nname = "a"\n')
    assert '[[item]]\nname = "b"' in text   # appended without disturbing the first
    assert _toml.read_table_array(path, "item", _Err) == [{"name": "a"}, {"name": "b"}]


def test_append_entry_wraps_a_write_failure(tmp_path):
    with pytest.raises(_Err):
        _toml.append_entry(tmp_path, "item", [("name", "a")], _Err)  # a directory, not a file


def test_append_entry_preserves_a_comment_only_file(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text("# keep me\n", encoding="utf-8")
    _toml.append_entry(path, "item", [("name", "a")], _Err)
    assert path.read_text(encoding="utf-8") == '# keep me\n\n[[item]]\nname = "a"\n'


def test_append_entry_wraps_a_save_failure(tmp_path, monkeypatch):
    # A directory path fails at load; this pins the other arm -- a failure inside save() is
    # wrapped in the domain error too (with the OSError chained), not left to escape raw.
    class _FailingDoc:
        def append_to_array(self, table, fields):
            pass

        def save(self, path):
            raise OSError("disk full")

    monkeypatch.setattr(TOMLEditor, "load", lambda path: _FailingDoc())
    with pytest.raises(_Err) as excinfo:
        _toml.append_entry(tmp_path / "x.toml", "item", [("name", "a")], _Err)
    assert isinstance(excinfo.value.__cause__, OSError)


def test_update_entry_replaces_a_field_and_leaves_the_rest_byte_identical(tmp_path):
    path = tmp_path / "x.toml"
    before = ('# heading\n'
              '[[item]]\nname = "a"\nsel = "old"\n'
              '\n'
              '[[item]]\nname = "b"\nsel = "untouched"\n')
    path.write_text(before, encoding="utf-8")
    _toml.update_entry(path, "item", match_field="name", match_value="a",
                       fields=[("sel", "new")], error_cls=_Err)
    # only the matched block's field changes; comment, blank line and the other block stay put
    assert path.read_text(encoding="utf-8") == before.replace('sel = "old"', 'sel = "new"')


def test_update_entry_inserts_an_absent_field(tmp_path):
    path = tmp_path / "x.toml"
    path.write_text('[[item]]\nname = "a"\n', encoding="utf-8")
    _toml.update_entry(path, "item", match_field="name", match_value="a",
                       fields=[("sel", "added")], error_cls=_Err)
    assert _toml.read_table_array(path, "item", _Err) == [{"name": "a", "sel": "added"}]


def test_update_entry_raises_when_no_block_matches(tmp_path):
    # A mismatch is surfaced, not a silent no-op write, so a repair against a stale/padded key
    # cannot quietly persist nothing.
    path = tmp_path / "x.toml"
    path.write_text('[[item]]\nname = "a"\n', encoding="utf-8")
    with pytest.raises(_Err):
        _toml.update_entry(path, "item", match_field="name", match_value="missing",
                           fields=[("sel", "new")], error_cls=_Err)
