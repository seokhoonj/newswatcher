import pytest
from thinchat.errors import ThinchatError

import newswatcher.summarize as summarize
from newswatcher.categories import Category
from newswatcher.errors import LLMError
from newswatcher.feed import FeedItem


class _FakeClient:
    model = "fake-model"
    def __init__(self, reply): self._reply = reply
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def complete(self, prompt, system=None): return self._reply


def test_summary_wraps_a_provider_error_as_llmerror(monkeypatch):
    # thinchat scrubs any provider key from its own ThinchatError; newswatcher's job is only to
    # wrap that error as an LLMError so a caller catches one package's failure type.
    class _Raising(_FakeClient):
        def complete(self, prompt, system=None):
            raise ThinchatError("provider call failed")

    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _Raising(""))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    with pytest.raises(LLMError):
        summarize.summarize_article(item, "body")


def test_summary_error_never_carries_the_api_key(monkeypatch):
    # As in heal: newswatcher relies on thinchat to scrub its own errors, and this pins that
    # newswatcher's own LLMError composition never re-adds the key it was handed.
    class _Raising(_FakeClient):
        def complete(self, prompt, system=None):
            raise ThinchatError("provider call failed")   # scrubbed: carries no key

    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _Raising(""))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    with pytest.raises(LLMError) as excinfo:
        summarize.summarize_article(item, "body", api_key="SENTINEL-KEY-abc123")
    chain = []
    err: BaseException | None = excinfo.value
    while err is not None:
        chain.append(str(err))
        err = err.__cause__
    assert all("SENTINEL-KEY-abc123" not in text for text in chain)


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


def test_summarize_classifies_when_categories_given(monkeypatch):
    monkeypatch.setattr(summarize, "make_llm_client",
                        lambda *a, **k: _FakeClient("규제·자본\n\n금감원이 규제를 강화했다."))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    categories = (Category("재보험·갱신"), Category("규제·자본"), Category("기타"))
    result = summarize.summarize_article(item, "body", categories=categories)
    assert result.category == "규제·자본"
    assert result.text == "금감원이 규제를 강화했다."


def test_summarize_category_empty_when_reply_names_no_known_category(monkeypatch):
    # The model ignored the classification format and just wrote a summary: keep the
    # summary, leave the category empty rather than mis-assigning.
    monkeypatch.setattr(summarize, "make_llm_client",
                        lambda *a, **k: _FakeClient("그냥 요약문입니다."))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    result = summarize.summarize_article(item, "body", categories=(Category("규제·자본"),))
    assert result.category == ""
    assert result.text == "그냥 요약문입니다."


def test_summarize_without_categories_leaves_category_empty(monkeypatch):
    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _FakeClient("요약"))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    assert summarize.summarize_article(item, "body").category == ""


def test_summarize_sends_category_names_and_hints_to_the_model(monkeypatch):
    seen = {}

    class _Rec(_FakeClient):
        def complete(self, prompt, system=None):
            seen["prompt"] = prompt
            seen["system"] = system
            return self._reply

    monkeypatch.setattr(summarize, "make_llm_client",
                        lambda *a, **k: _Rec("규제·자본\n\n요약"))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    categories = (Category("규제·자본", hint="K-ICS·지급여력"), Category("기타", hint="일반"))
    summarize.summarize_article(item, "body", categories=categories)
    assert "규제·자본" in seen["prompt"] and "K-ICS·지급여력" in seen["prompt"]
    assert "기타" in seen["prompt"] and "일반" in seen["prompt"]
    assert "classify" in seen["system"].lower()


@pytest.mark.parametrize("reply, expected_category, expected_text", [
    ("규제·자본\n\n금감원 요약", "규제·자본", "금감원 요약"),
    ("  규제·자본  \n\n요약", "규제·자본", "요약"),
    ("m&a\n\n딜 요약", "M&A", "딜 요약"),
    ("규제·자본\n요약", "", "규제·자본\n요약"),
    ("규제·자본\r\n\r\n금감원 요약", "규제·자본", "금감원 요약"),
    ("규제·자본\n \n요약", "규제·자본", "요약"),
    ("그냥 요약문", "", "그냥 요약문"),
])
def test_summarize_category_format_variants(monkeypatch, reply, expected_category, expected_text):
    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _FakeClient(reply))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    categories = (Category("규제·자본"), Category("M&A"))
    result = summarize.summarize_article(item, "body", categories=categories)
    assert result.category == expected_category
    assert result.text == expected_text


def test_summarize_rejects_a_reply_that_is_only_a_category(monkeypatch):
    # A reply of just the category name leaves an empty summary; the article is not
    # silently shipped without one -- it raises and is retried next poll.
    monkeypatch.setattr(summarize, "make_llm_client", lambda *a, **k: _FakeClient("규제·자본"))
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    with pytest.raises(LLMError):
        summarize.summarize_article(item, "body", categories=(Category("규제·자본"),))


@pytest.mark.parametrize("categories, expected_max_tokens, classifies", [
    ((), 320, False),                                       # classification off: the token cap is unchanged
    ((Category("규제·자본"), Category("기타")), 360, True),   # classifying: extra headroom for the category line
])
def test_summarize_token_budget_and_system_depend_on_classifying(
        monkeypatch, categories, expected_max_tokens, classifies):
    seen = {}

    class _Rec(_FakeClient):
        def complete(self, prompt, system=None):
            seen["system"] = system
            seen["prompt"] = prompt
            return self._reply

    def fake_make(*a, **k):
        seen["max_tokens"] = k["max_tokens"]
        return _Rec("규제·자본\n\n요약" if classifies else "요약")

    monkeypatch.setattr(summarize, "make_llm_client", fake_make)
    item = FeedItem(title="t", link="u", guid="g", source_name="s")
    summarize.summarize_article(item, "body", categories=categories)
    assert seen["max_tokens"] == expected_max_tokens
    assert ("classify" in seen["system"].lower()) is classifies
    assert ("Categories:" in seen["prompt"]) is classifies
