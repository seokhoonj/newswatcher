import json
from datetime import datetime

import pytest

from newswatch.errors import ArchiveError
from newswatch.store import Article, FileStore


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


def test_load_falls_back_to_saved_at_when_published_empty(tmp_path, monkeypatch):
    import newswatch.store as store_mod

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
    # A file written by a newer newswatch is read as absent, like a corrupt file, so
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
