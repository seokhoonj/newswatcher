import pytest

from newswatcher.errors import SourceError
from newswatcher.sources import Source, add_source, load_sources, update_selectors


def test_region_round_trips(tmp_path):
    path = tmp_path / "sources.toml"
    add_source(Source("KR paper", url="https://k/rss", region="kr"), path)
    add_source(Source("Intl wire", url="https://i/rss", region="intl"), path)
    assert {s.name: s.region for s in load_sources(path)} == {"KR paper": "kr", "Intl wire": "intl"}


def test_empty_region_is_omitted_and_reads_back_empty(tmp_path):
    path = tmp_path / "sources.toml"
    add_source(Source("Plain feed", url="https://n/rss"), path)
    assert "region =" not in path.read_text(encoding="utf-8")   # nothing to write when unset
    assert load_sources(path)[0].region == ""


def test_invalid_region_raises(tmp_path):
    path = tmp_path / "sources.toml"
    path.write_text('[[source]]\nname = "x"\nurl = "https://x/rss"\nregion = "usa"\n',
                    encoding="utf-8")
    with pytest.raises(SourceError):
        load_sources(path)


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
