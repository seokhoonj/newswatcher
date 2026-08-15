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


def test_load_is_oldest_first(tmp_path):
    store = FileStore(tmp_path)
    store.save(_article("late", "2026-08-20T00:00:00Z"))
    store.save(_article("early", "2026-08-01T00:00:00Z"))
    assert [a.guid for a in store.load()] == ["early", "late"]
