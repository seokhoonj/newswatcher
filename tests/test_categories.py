import pytest

from newswatcher.categories import Category, add_category, load_categories
from newswatcher.errors import CategoryError


def test_load_categories_absent_is_empty(tmp_path):
    assert load_categories(tmp_path / "categories.toml") == ()


def test_add_then_load_roundtrip(tmp_path):
    path = tmp_path / "categories.toml"
    add_category(Category("규제·자본", hint="K-ICS, 지급여력"), path)
    add_category(Category("기타"), path)
    loaded = load_categories(path)
    assert [category.name for category in loaded] == ["규제·자본", "기타"]
    assert loaded[0].hint == "K-ICS, 지급여력"
    assert loaded[1].hint == ""


def test_add_category_is_idempotent_by_name(tmp_path):
    path = tmp_path / "categories.toml"
    assert add_category(Category("규제·자본"), path) is True
    assert add_category(Category("규제·자본", hint="different"), path) is False   # no-op
    assert len(load_categories(path)) == 1


def test_load_rejects_a_category_missing_name(tmp_path):
    path = tmp_path / "categories.toml"
    path.write_text('[[category]]\nhint = "no name"\n', encoding="utf-8")
    with pytest.raises(CategoryError):
        load_categories(path)


def test_load_rejects_a_non_string_hint(tmp_path):
    path = tmp_path / "categories.toml"
    path.write_text('[[category]]\nname = "x"\nhint = 5\n', encoding="utf-8")
    with pytest.raises(CategoryError):
        load_categories(path)


def test_load_categories_rejects_malformed_toml(tmp_path):
    path = tmp_path / "categories.toml"
    path.write_text("[[category]\nname = 'x'\n", encoding="utf-8")   # syntactically invalid TOML
    with pytest.raises(CategoryError):
        load_categories(path)


def test_load_categories_rejects_a_case_insensitive_name_collision(tmp_path):
    path = tmp_path / "categories.toml"
    # two names that differ only in case would collapse in the classifier's lookup
    path.write_text('[[category]]\nname = "Tech"\n\n[[category]]\nname = "tech"\n', encoding="utf-8")
    with pytest.raises(CategoryError):
        load_categories(path)


def test_add_category_rejects_a_case_insensitive_collision(tmp_path):
    path = tmp_path / "categories.toml"
    assert add_category(Category("Tech"), path) is True
    assert add_category(Category("tech"), path) is False        # case-insensitive duplicate -> no-op
    assert add_category(Category("  Tech  "), path) is False     # whitespace variant -> no-op
    loaded = load_categories(path)                              # the file stays loadable, one entry
    assert [category.name for category in loaded] == ["Tech"]


def test_add_category_rejects_an_empty_or_whitespace_name(tmp_path):
    path = tmp_path / "categories.toml"
    for blank in ("", "   "):
        with pytest.raises(CategoryError):
            add_category(Category(blank), path)
    assert not path.exists()   # nothing written, so a later load still succeeds


def test_add_category_omits_an_empty_hint(tmp_path):
    # A hintless category writes just the name line, matching the old renderer.
    path = tmp_path / "categories.toml"
    add_category(Category("기타"), path)
    assert path.read_text(encoding="utf-8") == '[[category]]\nname = "기타"\n'
