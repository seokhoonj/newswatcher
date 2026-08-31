from newswatch.feed import FeedItem, normalize_date, parse_feed


def test_normalize_date_iso_and_rfc822_to_utc():
    assert normalize_date("2026-08-15") == "2026-08-15T00:00:00Z"          # date-only
    assert normalize_date("2026-08-15T09:00:00+09:00") == "2026-08-15T00:00:00Z"  # ISO offset -> UTC
    assert normalize_date("Fri, 15 Aug 2026 09:00:00 +0900") == "2026-08-15T00:00:00Z"  # RFC 822
    assert normalize_date("2 hours ago") == ""                             # unparseable
    assert normalize_date("") == ""                                        # empty


def test_normalize_date_dotted_and_slash_forms():
    # The dotted/slash numeric stamps Korean news sites emit -- newswatch's target locale.
    assert normalize_date("2026.08.15") == "2026-08-15T00:00:00Z"
    assert normalize_date("2026.08.15 09:00") == "2026-08-15T09:00:00Z"
    assert normalize_date("2026/08/15 09:00:00") == "2026-08-15T09:00:00Z"
    assert normalize_date("2026/08/15") == "2026-08-15T00:00:00Z"

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>보험신보 - 전체기사</title>
<item><title>롯데손보 흑자전환</title>
<link>https://e.com/a/1</link>
<guid>https://e.com/a/1</guid>
<description>2분기 순이익 13억원</description>
<pubDate>Fri, 15 Aug 2026 09:00:00 +0900</pubDate></item>
<item><title>SGI 서울보증 개소</title><link>https://e.com/a/2</link>
<guid>https://e.com/a/2</guid><description>광화문금융센터</description></item>
</channel></rss>"""


def test_parse_feed_extracts_items():
    items = parse_feed(RSS, "보험신보")
    assert len(items) == 2
    assert isinstance(items[0], FeedItem)
    assert items[0].title == "롯데손보 흑자전환"
    assert items[0].link == "https://e.com/a/1"
    assert items[0].guid == "https://e.com/a/1"
    assert "13억원" in items[0].summary
    assert items[0].published.startswith("2026-08-15")
    assert items[0].source_name == "보험신보"


def test_parse_feed_missing_pubdate_is_empty_string():
    items = parse_feed(RSS, "보험신보")
    assert items[1].published == ""
