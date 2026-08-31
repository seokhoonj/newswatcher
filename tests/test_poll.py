from newswatch.errors import ArchiveError, FetchError, LLMError
from newswatch.feed import FeedItem
from newswatch.poll import poll_sources
from newswatch.robots import RobotsGate
from newswatch.sources import Source
from newswatch.state import State
from newswatch.store import FileStore
from newswatch.summarize import Summary
from newswatch.topics import Topic


class _Collect:
    """Stub the network: map source name -> items, and body text."""
    def __init__(self, items_by_source, body="본문"):
        self.items_by_source = items_by_source
        self.body = body


def _fake_summary(item, body, **k):
    return Summary(text=f"요약:{item.title}", model="m")


# Unused by these tests: _collect/_fetch_body are stubbed, so the gate is never read.
_gate = RobotsGate("newswatch-test", lambda url: None)


def test_poll_collects_matched_new_articles(tmp_path, monkeypatch):
    import newswatch.poll as poll
    src = Source("범용지", kind="rss", url="u", topics=("insurance",))
    items = (FeedItem(title="보험료 인상", link="https://e.com/1", guid="g1",
                      published="2026-08-15T00:00:00Z", source_name="범용지"),
             FeedItem(title="은행 뉴스", link="https://e.com/2", guid="g2",
                      published="2026-08-15T00:00:00Z", source_name="범용지"))
    monkeypatch.setattr(poll, "_collect", lambda s, g, sess: items if s.kind == "rss" else ())
    monkeypatch.setattr(poll, "_fetch_body", lambda item, s, g, sess: "본문")
    store = FileStore(tmp_path)
    report = poll_sources((src,), (Topic("insurance", includes=("보험",)),),
                          gate=_gate, state=State(), store=store, summarize=_fake_summary)
    assert len(report.collected) == 1
    assert report.collected[0].title == "보험료 인상"
    assert report.collected[0].summary == "요약:보험료 인상"
    assert len(store.load()) == 1


def test_second_poll_skips_seen(tmp_path, monkeypatch):
    import newswatch.poll as poll
    src = Source("전문지", kind="rss", url="u", topics=("insurance",), keep_all=True)
    items = (FeedItem(title="a", link="https://e.com/1", guid="g1",
                      published="2026-08-15T00:00:00Z", source_name="전문지"),)
    monkeypatch.setattr(poll, "_collect", lambda s, g, sess: items)
    monkeypatch.setattr(poll, "_fetch_body", lambda item, s, g, sess: "본문")
    state = State()
    store = FileStore(tmp_path)
    r1 = poll_sources((src,), (Topic("insurance"),), gate=_gate, state=state,
                      store=store, summarize=_fake_summary)
    r2 = poll_sources((src,), (Topic("insurance"),), gate=_gate, state=state,
                      store=store, summarize=_fake_summary)
    assert len(r1.collected) == 1 and len(r2.collected) == 0


def test_poll_degrades_on_summary_error(tmp_path, monkeypatch):
    import newswatch.poll as poll
    src = Source("지", kind="rss", url="u", topics=("t",), keep_all=True)
    items = (FeedItem(title="a", link="https://e.com/1", guid="g1",
                      published="2026-08-15T00:00:00Z", source_name="지"),
             FeedItem(title="b", link="https://e.com/2", guid="g2",
                      published="2026-08-15T00:00:00Z", source_name="지"))
    monkeypatch.setattr(poll, "_collect", lambda s, g, sess: items)
    monkeypatch.setattr(poll, "_fetch_body", lambda item, s, g, sess: "본문")

    def summarize(item, body, **k):
        if item.guid == "g1":
            raise LLMError("boom")
        return Summary(text="ok", model="m")

    state = State()
    report = poll_sources((src,), (Topic("t"),), gate=_gate, state=state,
                          store=FileStore(tmp_path), summarize=summarize)
    # one bad article does not abort the poll; the good one is still collected
    assert [a.guid for a in report.collected] == ["g2"]
    assert any("e.com/1" in name for name, _ in report.skipped)
    # the failed article is left unmarked, so a transient outage retries it next poll
    assert state.is_new("지", items[0]) is True
    assert state.is_new("지", items[1]) is False


def test_poll_degrades_on_store_error(tmp_path, monkeypatch):
    import newswatch.poll as poll
    src = Source("지", kind="rss", url="u", topics=("t",), keep_all=True)
    items = (FeedItem(title="a", link="https://e.com/1", guid="g1",
                      published="2026-08-15T00:00:00Z", source_name="지"),)
    monkeypatch.setattr(poll, "_collect", lambda s, g, sess: items)
    monkeypatch.setattr(poll, "_fetch_body", lambda item, s, g, sess: "본문")

    class BadStore(FileStore):
        def save(self, article):
            raise ArchiveError("disk full")

    state = State()
    report = poll_sources((src,), (Topic("t"),), gate=_gate, state=state,
                          store=BadStore(tmp_path), summarize=_fake_summary)
    assert report.collected == ()
    assert any("e.com/1" in name for name, _ in report.skipped)
    assert state.is_new("지", items[0]) is True   # unmarked -> retry next poll


def test_poll_skips_a_failed_source_and_collects_a_later_one(tmp_path, monkeypatch):
    import newswatch.poll as poll
    bad = Source("깨진소스", kind="rss", url="u", topics=("t",), keep_all=True)
    good = Source("정상소스", kind="rss", url="u", topics=("t",), keep_all=True)
    items = (FeedItem(title="a", link="https://e.com/1", guid="g1",
                      published="2026-08-15T00:00:00Z", source_name="정상소스"),)

    def collect(s, g, sess):
        if s.name == "깨진소스":
            raise FetchError("feed returned 500")
        return items

    monkeypatch.setattr(poll, "_collect", collect)
    monkeypatch.setattr(poll, "_fetch_body", lambda item, s, g, sess: "본문")
    report = poll_sources((bad, good), (Topic("t"),), gate=_gate, state=State(),
                          store=FileStore(tmp_path), summarize=_fake_summary)
    assert [a.guid for a in report.collected] == ["g1"]   # the later source still ran
    assert any(name == "깨진소스" for name, _ in report.skipped)


def test_empty_crawl_source_is_reported(tmp_path, monkeypatch):
    import newswatch.poll as poll
    src = Source("무RSS", kind="crawl", url="u", topics=("insurance",),
                 item="li", title="a", link="a@href")
    monkeypatch.setattr(poll, "_collect", lambda s, g, sess: ())
    state = State()
    report = poll_sources((src,), (Topic("insurance"),), gate=_gate, state=state,
                          store=FileStore(tmp_path), summarize=_fake_summary)
    assert report.empty_crawl_sources == ("무RSS",)
    assert state.empty_polls_by_source["무RSS"] == 1
