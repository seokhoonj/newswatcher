import pytest

from newswatcher.errors import SourceError
from newswatcher.sources import Source, add_source, load_sources, update_selectors


def test_rss_source_roundtrip(tmp_path):
    path = tmp_path / "sources.toml"
    src = Source("한국보험신문", kind="rss",
                 url="https://www.insnews.co.kr/rss/allArticle.xml",
                 topics=("insurance",), keep_all=True)
    assert add_source(src, path) is True
    assert add_source(src, path) is False  # duplicate name
    loaded = load_sources(path)
    assert loaded[0].kind == "rss"
    assert loaded[0].keep_all is True
    assert loaded[0].topics == ("insurance",)


def test_crawl_source_requires_selectors(tmp_path):
    path = tmp_path / "sources.toml"
    path.write_text(
        '[[source]]\nname = "x"\nkind = "crawl"\nurl = "https://e.com/list"\n'
        'topics = ["insurance"]\n', encoding="utf-8")
    with pytest.raises(SourceError):
        load_sources(path)  # crawl needs item/title/link


def test_unknown_kind_rejected(tmp_path):
    path = tmp_path / "sources.toml"
    path.write_text('[[source]]\nname="x"\nkind="ftp"\nurl="u"\n', encoding="utf-8")
    with pytest.raises(SourceError):
        load_sources(path)


def test_update_selectors_rewrites_in_place(tmp_path):
    path = tmp_path / "sources.toml"
    add_source(Source("s", kind="crawl", url="https://e.com/list",
                      topics=("t",), item="li", title="a", link="a@href"), path)
    update_selectors("s", {"item": "ul.new li", "title": "a.tit"}, path)
    src = load_sources(path)[0]
    assert src.item == "ul.new li"
    assert src.title == "a.tit"
    assert src.link == "a@href"  # unchanged keys preserved


def test_add_source_omits_default_topics_and_keep_all(tmp_path):
    # An unset topics / keep_all=False source writes only the required fields, matching the
    # old renderer (the optional lines are left out, not written as empty/false).
    path = tmp_path / "sources.toml"
    add_source(Source("s", kind="rss", url="https://e.com"), path)
    assert path.read_text(encoding="utf-8") == (
        '[[source]]\nname = "s"\nkind = "rss"\nurl = "https://e.com"\n')


def test_add_source_rejects_an_empty_or_whitespace_name(tmp_path):
    path = tmp_path / "sources.toml"
    for blank in ("", "   "):
        with pytest.raises(SourceError):
            add_source(Source(blank, kind="rss", url="https://e.com"), path)
    assert not path.exists()   # nothing written, so a later load still succeeds
