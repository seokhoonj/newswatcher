import pytest

from newswatcher import _toml


class _Err(Exception):
    pass


def test_quote_escapes_and_keeps_non_ascii():
    assert _toml.quote('na"me') == '"na\\"me"'
    assert _toml.quote("보험") == '"보험"'   # non-ASCII kept verbatim


def test_array_renders_inline_list():
    assert _toml.array(()) == "[]"
    assert _toml.array(("a", "b")) == '["a", "b"]'


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
