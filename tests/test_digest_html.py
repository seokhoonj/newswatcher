from newswatcher.digest_html import render_html
from newswatcher.store import Article
from newswatcher.stories import Story


def _article(title, source, region, topic, published="2026-09-03T08:00:00Z", summary="요약."):
    return Article(guid=source + title, title=title, link=f"https://e.com/{source}",
                   source_name=source, published=published, topics=(topic,), region=region,
                   summary=summary)


def _stories():
    return (
        Story(lead=_article("재보험 갱신 요율 둔화", "Reinsurance News", "intl", "재보험"),
              duplicates=(_article("갱신 요율 둔화 전망", "Commercial Risk", "intl", "재보험"),)),
        Story(lead=_article("K-ICS 자본확충 압박", "한국보험신문", "kr", "규제")),
        Story(lead=_article("장기손해율 개선", "보험매일", "kr", "손해율")),
    )


def test_render_is_self_contained():
    html = render_html(_stories(), title="브리핑", period_label="오늘", generated_at="2026-09-03")
    # No external resource loads -- the page must open the same from a file:// path.
    assert "<script src" not in html
    assert "<link" not in html
    assert "cdn" not in html.lower()
    assert "@import" not in html


def test_render_escapes_content():
    story = Story(lead=_article('<script>alert(1)</script>', "S&P", "kr", "규제"))
    html = render_html((story,), title="<b>제목</b>", period_label="오늘", generated_at="now")
    assert "<script>alert(1)</script>" not in html   # the payload is escaped, not injected
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "S&amp;P" in html
    assert "<b>제목</b>" not in html


def test_render_splits_regions_with_domestic_first():
    html = render_html(_stories(), title="브리핑", period_label="오늘", generated_at="now")
    assert 'data-region="kr"' in html and 'data-region="intl"' in html
    # 국내 tab and its cards come before 해외 -- the primary audience leads.
    assert html.index("국내") < html.index("해외")
    assert html.index('data-region="kr"') < html.index('data-region="intl"')


def test_render_counts_articles_and_merges():
    # 3 stories folded from 4 articles (one story has a duplicate) -> 1 merged.
    html = render_html(_stories(), title="브리핑", period_label="오늘", generated_at="now")
    assert "<b>4</b>건" in html          # 4 source articles collected
    assert "<b>3</b>개 스토리" in html   # 3 stories after dedup
    assert "중복 1건 병합" in html       # 4 - 3 = 1 merged


def test_render_groups_and_tags_topics():
    html = render_html(_stories(), title="브리핑", period_label="오늘", generated_at="now")
    for topic in ("재보험", "규제", "손해율"):
        assert f'data-topic="{topic}"' in html


def test_render_empty_digest_is_valid():
    html = render_html((), title="브리핑", period_label="지난 7일", generated_at="now")
    assert "없습니다" in html               # a friendly empty state
    assert "<b>0</b>개 스토리" in html
    assert "<style>" in html and "</style>" in html
