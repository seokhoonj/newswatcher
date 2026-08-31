import pytest
from thinchat.errors import ThinchatError

import newswatch.summarize as summarize
from newswatch.errors import LLMError
from newswatch.feed import FeedItem


class _FakeClient:
    model = "fake-model"
    def __init__(self, reply): self._reply = reply
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def complete(self, prompt, system=None): return self._reply


def test_summary_error_hides_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET-KEY-123")

    class _Raising(_FakeClient):
        def complete(self, prompt, system=None):
            raise ThinchatError("HTTP 401 at https://gen.../v1?key=SECRET-KEY-123")

    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _Raising(""))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    with pytest.raises(LLMError) as excinfo:
        summarize.summarize_article(item, "body")
    assert "SECRET-KEY-123" not in str(excinfo.value)


def test_summarize_article_uses_body(monkeypatch):
    def fake_make(*a, **k):
        return _FakeClient(" 보험료가 올랐다는 기사. ")
    monkeypatch.setattr(summarize, "make_llm_client", fake_make)
    item = FeedItem(title="보험료 인상", link="https://e.com/1", guid="g", source_name="s")
    result = summarize.summarize_article(item, "본문 전문 텍스트")
    assert result.text == "보험료가 올랐다는 기사."
    assert result.model == "fake-model"


def test_summarize_falls_back_to_feed_text_when_body_empty(monkeypatch):
    seen = {}
    class Rec(_FakeClient):
        def complete(self, prompt, system=None):
            seen["prompt"] = prompt
            return "요약"
    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: Rec("요약"))
    item = FeedItem(title="제목", link="u", guid="g", summary="피드 요약", source_name="s")
    summarize.summarize_article(item, "")
    assert "제목" in seen["prompt"] and "피드 요약" in seen["prompt"]
