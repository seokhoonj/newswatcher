from newswatcher.body import extract_body
from newswatcher.sources import Source

PAGE = """<html><body><nav>menu</nav>
<div class="article-body"><p>보험료가 오른다.</p><p>손해율 상승 때문이다.</p></div>
<footer>copyright</footer></body></html>"""


def test_body_selector_extracts_just_that_node():
    src = Source("s", kind="crawl", url="u", topics=("t",), item="li",
                 title="a", link="a@href", body_selector="div.article-body")
    body = extract_body(PAGE, src)
    assert "보험료가 오른다" in body
    assert "손해율 상승" in body
    assert "menu" not in body and "copyright" not in body


def test_falls_back_to_generic_when_no_selector():
    src = Source("s", kind="rss", url="u", topics=("t",))
    body = extract_body(PAGE, src)
    # trafilatura returns the main content; at minimum non-empty and containing body text
    assert "보험료" in body
