import pytest
from thinchat.errors import ThinchatError

import newswatch.heal as heal
from newswatch.errors import HealError
from newswatch.sources import Source, add_source, load_sources
from newswatch.state import State


def test_heal_error_hides_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")

    class _Raising:
        model = "m"
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def complete(self, prompt, system=None):
            raise ThinchatError("HTTP 401 at https://gen.../v1?key=SECRET-KEY-123")

    monkeypatch.setattr(heal, "_fetch_listing", lambda s, g, sess: HTML)
    monkeypatch.setattr(heal, "make_llm_client", lambda *a, **k: _Raising())
    with pytest.raises(HealError) as excinfo:
        heal.heal_source(BROKEN, gate=None)
    assert "SECRET-KEY-123" not in str(excinfo.value)

BROKEN = Source("무RSS", kind="crawl", url="https://e.com/list", topics=("t",),
                item="ul.OLD li", title="a.old", link="a.old@href")

# The live HTML now uses different classes than the stored selectors.
HTML = """<ul class="new"><li class="row">
<a class="tit" href="/a/1">보험료 인상</a></li>
<li class="row"><a class="tit" href="/a/2">손해율</a></li></ul>"""


def test_needs_heal_only_after_threshold():
    st = State()
    assert heal.needs_heal(BROKEN, st) is False
    st.note_empty("무RSS")
    assert heal.needs_heal(BROKEN, st) is False   # 1 < 2
    st.note_empty("무RSS")
    assert heal.needs_heal(BROKEN, st) is True     # 2 >= 2


def test_heal_applies_validated_selectors(tmp_path, monkeypatch):
    path = tmp_path / "sources.toml"
    add_source(BROKEN, path)
    monkeypatch.setattr(heal, "_fetch_listing", lambda s, g, sess: HTML)
    # LLM proposes the correct new selectors
    monkeypatch.setattr(heal, "propose_selectors",
                        lambda html, s, **k: {"item": "ul.new li.row", "title": "a.tit",
                                              "link": "a.tit@href"})
    result = heal.heal_source(BROKEN, gate=None, path=path)
    assert result is not None and result.applied is True
    assert result.new["item"] == "ul.new li.row"
    # persisted
    assert load_sources(path)[0].item == "ul.new li.row"


def test_heal_rejects_selectors_that_still_extract_nothing(tmp_path, monkeypatch):
    path = tmp_path / "sources.toml"
    add_source(BROKEN, path)
    monkeypatch.setattr(heal, "_fetch_listing", lambda s, g, sess: HTML)
    monkeypatch.setattr(heal, "propose_selectors",
                        lambda html, s, **k: {"item": "ul.STILLWRONG li", "title": "a",
                                              "link": "a@href"})
    result = heal.heal_source(BROKEN, gate=None, path=path)
    assert result is not None and result.applied is False
    assert load_sources(path)[0].item == "ul.OLD li"  # unchanged


def test_heal_returns_none_when_source_healthy(monkeypatch):
    healthy = Source("ok", kind="crawl", url="u", topics=("t",),
                     item="ul.new li.row", title="a.tit", link="a.tit@href")
    monkeypatch.setattr(heal, "_fetch_listing", lambda s, g, sess: HTML)
    assert heal.heal_source(healthy, gate=None) is None
