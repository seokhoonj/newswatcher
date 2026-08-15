from newswatch.crawl import extract_items, parse_selector
from newswatch.sources import Source

HTML = """<html><body><ul class="list">
<li class="row"><a class="tit" href="/a/1">보험료 인상</a><span class="date">2026-08-15</span></li>
<li class="row"><a class="tit" href="https://e.com/a/2">손해율 급등</a><span class="date">2026-08-14</span></li>
</ul></body></html>"""

SRC = Source("무RSS신문", kind="crawl", url="https://e.com/insurance/list",
             topics=("insurance",), item="li.row", title="a.tit",
             link="a.tit@href", date="span.date")


def test_parse_selector_splits_attr():
    assert parse_selector("a.tit@href") == ("a.tit", "href")
    assert parse_selector("span.date") == ("span.date", None)


def test_extract_items_reads_rows():
    items = extract_items(HTML, SRC)
    assert len(items) == 2
    assert items[0].title == "보험료 인상"
    assert items[0].link == "https://e.com/a/1"  # relative resolved against source url
    assert items[0].published == "2026-08-15"
    assert items[0].source_name == "무RSS신문"
    assert items[1].link == "https://e.com/a/2"  # absolute kept


def test_extract_skips_rows_without_link():
    html = '<ul class="list"><li class="row"><a class="tit">no link</a></li></ul>'
    assert extract_items(html, SRC) == ()
