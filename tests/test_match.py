from newswatch.feed import FeedItem
from newswatch.match import assign_topics, matches_topic, topics_for
from newswatch.sources import Source
from newswatch.topics import Topic

INS = Topic("insurance", includes=("보험", "손보"), excludes=("광고",))


def _item(title, summary=""):
    return FeedItem(title=title, link="u", guid="u", summary=summary, source_name="s")


def test_matches_on_title_or_summary():
    assert matches_topic(_item("보험료 인상"), INS) is True
    assert matches_topic(_item("금리", "손보사 실적"), INS) is True
    assert matches_topic(_item("은행 뉴스"), INS) is False


def test_excludes_drop_match():
    assert matches_topic(_item("보험 광고 특집"), INS) is False


def test_empty_includes_matches_all():
    assert matches_topic(_item("anything"), Topic("all")) is True


def test_keep_all_source_tags_without_filter():
    src = Source("전문지", kind="rss", url="u", topics=("insurance",), keep_all=True)
    assert topics_for(_item("은행 뉴스"), src, (INS,)) == ("insurance",)


def test_filtered_source_tags_only_matches():
    src = Source("범용지", kind="rss", url="u", topics=("insurance",))
    assert topics_for(_item("은행 뉴스"), src, (INS,)) == ()
    assert topics_for(_item("보험 뉴스"), src, (INS,)) == ("insurance",)


def test_assign_topics_returns_none_on_no_match():
    src = Source("범용지", kind="rss", url="u", topics=("insurance",))
    assert assign_topics(_item("은행"), src, (INS,)) is None
    tagged = assign_topics(_item("보험"), src, (INS,))
    assert tagged is not None and tagged.topics == ("insurance",)
