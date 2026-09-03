import json
from datetime import datetime

import pytest

from newswatcher.errors import ArchiveError
from newswatcher.store import Article, FileStore


def _article(guid, published, topics=("insurance",), title="t"):
    return Article(guid=guid, title=title, link=f"https://e.com/{guid}",
                   source_name="s", published=published, topics=topics,
                   summary="our summary", summary_model="m")


def test_save_then_load_roundtrip(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z"))
    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].guid == "a1"
    assert loaded[0].summary == "our summary"


def test_save_and_load_preserves_region(tmp_path):
    store = FileStore(tmp_path)
    store.save(Article(guid="i", title="Global rates", link="https://e/i", source_name="s",
                       published="2026-08-16T00:00:00Z", topics=("t",), region="intl",
                       summary="x"))
    store.save(Article(guid="k", title="코스피", link="https://e/k", source_name="s",
                       published="2026-08-15T00:00:00Z", topics=("t",), region="kr",
                       summary="x"))
    assert {a.guid: a.region for a in store.load()} == {"i": "intl", "k": "kr"}


def test_v1_file_without_region_infers_from_title(tmp_path):
    articles = tmp_path / "articles"
    articles.mkdir(parents=True)

    def write_v1(name, title):
        envelope = {"schema_version": 1, "saved_at": "2026-08-15T00:00:00Z",
                    "article": {"guid": name, "title": title, "link": "l", "source_name": "s",
                                "published": "2026-08-15T00:00:00Z", "topics": ["t"],
                                "summary": "x"}}
        (articles / f"{name}.json").write_text(json.dumps(envelope), encoding="utf-8")

    write_v1("kr", "코스피 3000 돌파")
    write_v1("en", "Market rally continues")
    by_title = {a.title: a.region for a in FileStore(tmp_path).load()}
    assert by_title["코스피 3000 돌파"] == "kr"        # inferred from the Korean title
    assert by_title["Market rally continues"] == "intl"


def test_forward_schema_file_is_read_as_absent(tmp_path):
    articles = tmp_path / "articles"
    articles.mkdir(parents=True)
    envelope = {"schema_version": 99, "saved_at": "2026-08-15T00:00:00Z",
                "article": {"guid": "g", "title": "t", "link": "l", "source_name": "s",
                            "published": "", "topics": [], "summary": "x"}}
    (articles / "g.json").write_text(json.dumps(envelope), encoding="utf-8")
    assert FileStore(tmp_path).load() == ()   # a newer schema is skipped, not fatal


def test_save_is_idempotent_by_guid(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z", title="first"))
    store.save(_article("a1", "2026-08-15T00:00:00Z", title="second"))
    loaded = store.load()
    assert len(loaded) == 1 and loaded[0].title == "second"


def test_load_filters_by_topic_and_date(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-10T00:00:00Z", topics=("insurance",)))
    store.save(_article("a2", "2026-08-20T00:00:00Z", topics=("banking",)))
    assert {a.guid for a in store.load(topic="insurance")} == {"a1"}
    assert {a.guid for a in store.load(since="2026-08-15")} == {"a2"}


def test_load_date_range_is_half_open(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("at_since", "2026-08-10T00:00:00Z"))
    store.save(_article("mid", "2026-08-12T00:00:00Z"))
    store.save(_article("at_until", "2026-08-15T00:00:00Z"))
    got = {a.guid for a in store.load(since="2026-08-10T00:00:00Z",
                                      until="2026-08-15T00:00:00Z")}
    assert got == {"at_since", "mid"}   # since inclusive, until exclusive


class _FixedDatetime:
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 9, 15, 12, 0, 0, tzinfo=tz)


def test_prune_removes_only_articles_older_than_the_window(tmp_path, monkeypatch):
    import newswatcher.store as store_mod

    monkeypatch.setattr(store_mod, "datetime", _FixedDatetime)   # pin "now" so the cutoff is fixed
    store = FileStore(tmp_path)
    store.save(_article("old", "2026-07-01T00:00:00Z"))      # 76 days back
    store.save(_article("recent", "2026-09-10T00:00:00Z"))   # 5 days back
    removed = store.prune_older_than(30)   # cutoff = 2026-08-16
    assert removed == 1
    assert {a.guid for a in store.load()} == {"recent"}


def test_prune_keeps_an_undated_article_within_the_window(tmp_path, monkeypatch):
    import newswatcher.store as store_mod

    monkeypatch.setattr(store_mod, "datetime", _FixedDatetime)
    store = FileStore(tmp_path)
    store.save(_article("undated", ""))   # no published date -> dated by saved_at (= now)
    assert store.prune_older_than(30) == 0
    assert {a.guid for a in store.load()} == {"undated"}


def test_prune_leaves_corrupt_files_in_place(tmp_path, monkeypatch):
    import newswatcher.store as store_mod

    monkeypatch.setattr(store_mod, "datetime", _FixedDatetime)
    store = FileStore(tmp_path)
    store.save(_article("old", "2026-01-01T00:00:00Z"))
    corrupt = tmp_path / "articles" / "deadbeef.json"
    corrupt.write_text("{not json", encoding="utf-8")   # unparseable: never deleted on a guess
    assert store.prune_older_than(30) == 1   # only the dated, old article
    assert corrupt.exists()


def test_prune_rejects_a_non_positive_window(tmp_path):
    with pytest.raises(ValueError):
        FileStore(tmp_path).prune_older_than(0)


def test_load_falls_back_to_saved_at_when_published_empty(tmp_path, monkeypatch):
    import newswatcher.store as store_mod

    class _FixedDatetime:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 15, 12, 0, 0, tzinfo=tz)

    monkeypatch.setattr(store_mod, "datetime", _FixedDatetime)   # pin saved_at deterministically
    store = FileStore(tmp_path)
    store.save(_article("no_date", ""))   # empty published -> filtered/ordered by saved_at
    assert {a.guid for a in store.load(since="2026-08-15", until="2026-08-16")} == {"no_date"}
    assert store.load(until="2026-08-15") == ()    # until is exclusive of the saved day
    assert store.load(since="2026-08-16") == ()    # window after the saved day


def test_load_is_oldest_first(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("late", "2026-08-20T00:00:00Z"))
    store.save(_article("early", "2026-08-01T00:00:00Z"))
    assert [a.guid for a in store.load()] == ["early", "late"]


def test_load_skips_a_corrupt_file(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z"))
    (tmp_path / "articles" / "garbage.json").write_text("{ not json", encoding="utf-8")
    loaded = store.load()
    assert [a.guid for a in loaded] == ["a1"]   # the unreadable file is read as absent


def test_load_skips_a_file_missing_required_fields(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z"))
    envelope = {"schema_version": 1, "saved_at": "2026-08-15T00:00:00Z",
                "article": {"guid": "x"}}   # missing title/link/etc.
    (tmp_path / "articles" / "partial.json").write_text(json.dumps(envelope),
                                                        encoding="utf-8")
    assert [a.guid for a in store.load()] == ["a1"]


def test_load_skips_a_forward_schema_version(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z"))
    envelope = {"schema_version": 999, "saved_at": "2026-08-15T00:00:00Z",
                "article": {}}
    (tmp_path / "articles" / "future.json").write_text(json.dumps(envelope),
                                                       encoding="utf-8")
    # A file written by a newer newswatcher is read as absent, like a corrupt file, so
    # one forward-schema file does not sink the whole archive read.
    assert [a.guid for a in store.load()] == ["a1"]


def test_load_raises_on_an_unreadable_file(tmp_path, monkeypatch):
    store = FileStore(tmp_path)
    store.save(_article("a1", "2026-08-15T00:00:00Z"))

    def _boom(self, *a, **k):
        raise OSError("permission denied")

    monkeypatch.setattr("pathlib.Path.read_text", _boom)
    with pytest.raises(ArchiveError):
        store.load()
