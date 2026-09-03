from newswatcher.region import infer_region, region_label, resolve_region


def test_infer_region_by_hangul():
    assert infer_region("코스피 3000 돌파") == "kr"
    assert infer_region("K-ICS 자본확충") == "kr"          # mixed Latin + Hangul -> kr
    assert infer_region("Reinsurance rates rise") == "intl"
    assert infer_region("AI") == "intl"
    assert infer_region("") == "intl"


def test_resolve_region_explicit_wins_else_infers():
    assert resolve_region("kr", "English title") == "kr"      # explicit overrides the guess
    assert resolve_region("intl", "한글 제목") == "intl"
    assert resolve_region("", "한글 제목") == "kr"            # unset -> infer
    assert resolve_region("", "English title") == "intl"
    assert resolve_region("bogus", "한글 제목") == "kr"       # a typo falls back to inference


def test_region_label():
    assert region_label("kr") == "국내"
    assert region_label("intl") == "해외"
    assert region_label("mars") == "mars"                     # unknown code renders itself
