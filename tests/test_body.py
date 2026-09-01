import pytest

from newswatcher.body import extract_body
from newswatcher.errors import SourceError
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


def test_malformed_body_selector_raises_sourceerror():
    # A bad body_selector must be the domain error (the poll's body-fetch then degrades to
    # feed text), not a bare soupsieve crash.
    src = Source("s", kind="crawl", url="u", topics=("t",), item="li",
                 title="a", link="a@href", body_selector=">>bad")
    with pytest.raises(SourceError):
        extract_body("<html><div>x</div></html>", src)


def test_unsupported_pseudo_body_selector_raises_sourceerror():
    src = Source("s", kind="crawl", url="u", topics=("t",), item="li",
                 title="a", link="a@href", body_selector="div::text")
    with pytest.raises(SourceError):
        extract_body("<html><div>x</div></html>", src)


def test_falls_back_to_generic_when_no_selector():
    src = Source("s", kind="rss", url="u", topics=("t",))
    body = extract_body(PAGE, src)
    # trafilatura returns the main content; at minimum non-empty and containing body text
    assert "보험료" in body
