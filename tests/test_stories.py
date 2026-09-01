from newswatch.store import Article
from newswatch.stories import Story, group_stories, title_similarity


def _article(title, *, link=None, source="s", topic="t"):
    link = link or f"https://e.com/{title}"
    return Article(guid=link, title=title, link=link, source_name=source,
                   published="", topics=(topic,), summary="", summary_model="m")


# --- title_similarity ----------------------------------------------------------

def test_identical_titles_are_fully_similar():
    assert title_similarity("코스피 3000 돌파", "코스피 3000 돌파") == 1.0


def test_disjoint_titles_are_not_similar():
    assert title_similarity("코스피 3000 돌파", "환율 급등 우려") < 0.2


def test_korean_particle_and_punctuation_do_not_split_a_duplicate():
    # The case word-token overlap misses: 3000 vs 3000선, and the comma. Character
    # bigrams still overlap on almost everything.
    assert title_similarity("코스피 3000 돌파", "코스피, 3000선 돌파") >= 0.5


def test_a_near_duplicate_scores_above_an_unrelated_pair():
    near = title_similarity("Fed holds rates steady", "Fed keeps rates steady")
    far = title_similarity("Fed holds rates steady", "Nvidia earnings beat estimates")
    assert near > far
    assert near >= 0.5


def test_spacing_and_case_are_normalized_away():
    assert title_similarity("Chip Supply Crash", "chip  supply crash") == 1.0


def test_empty_titles_are_never_similar():
    assert title_similarity("", "") == 0.0
    assert title_similarity("", "코스피 3000 돌파") == 0.0


def test_titles_too_short_for_bigrams_compare_by_exact_equality():
    assert title_similarity("AI", "AI") == 1.0   # one bigram is too few to score; exact match
    assert title_similarity("AI", "ML") == 0.0


# --- group_stories -------------------------------------------------------------

def test_no_articles_yields_no_stories():
    assert group_stories(()) == ()


def test_a_lone_article_is_its_own_story_with_no_duplicates():
    (story,) = group_stories((_article("코스피 3000 돌파"),))
    assert story.duplicates == ()


def test_cross_source_duplicates_collapse_under_the_first_seen_lead():
    yonhap = _article("코스피 3000 돌파", source="yonhap")
    hankyung = _article("코스피, 3000선 돌파", source="hankyung")
    (story,) = group_stories((yonhap, hankyung))
    assert story.lead is yonhap                    # first collected leads the story
    assert story.duplicates == (hankyung,)
    assert story.also_reported_by == ("hankyung",)


def test_unrelated_articles_stay_separate():
    stories = group_stories((_article("코스피 3000 돌파"), _article("환율 급등 우려")))
    assert len(stories) == 2


def test_greedy_leader_does_not_chain_transitively():
    # a~b and (loosely) b~c, but a and c are unalike: c compares only to leads, so the
    # b link must not pull c into a's story.
    a = _article("금리 인상 우려 확산")
    b = _article("금리 인상 우려")     # near-duplicate of a -> joins a
    c = _article("금리 동결 결정")     # shares only 금리 with a -> its own story
    stories = group_stories((a, b, c))
    assert stories[0].lead is a and b in stories[0].duplicates
    assert stories[-1].lead is c and stories[-1].duplicates == ()


def test_lead_order_follows_first_appearance():
    first = _article("환율 급등 우려")
    second = _article("코스피 3000 돌파")
    assert [story.lead for story in group_stories((first, second))] == [first, second]


def test_threshold_is_tunable():
    pair = (_article("코스피 3000 돌파"), _article("코스피, 3000선 돌파"))
    assert len(group_stories(pair, threshold=0.99)) == 2   # nothing merges when strict
    assert len(group_stories(pair, threshold=0.10)) == 1   # everything merges when loose


def test_also_reported_by_excludes_the_leads_own_outlet():
    # A same-outlet re-headline (an original and its later 종합/update from the same
    # source) is still folded, but must not read as "also reported by: <the lead's outlet>".
    lead = _article("사고 속보", source="yonhap")
    same_outlet_update = _article("사고 속보 종합", source="yonhap")
    other_outlet = _article("사고 속보 상보", source="hankyung")
    story = Story(lead=lead, duplicates=(same_outlet_update, other_outlet))
    assert story.also_reported_by == ("hankyung",)   # yonhap is the lead, not "also"


def test_also_reported_by_drops_repeat_source_names_in_order():
    lead = _article("사고 속보", source="a")
    dup_b = _article("사고 속보!", source="b")
    dup_b2 = _article("사고 속보 상보", source="b")
    dup_c = _article("사고 속보 종합", source="c")
    story = Story(lead=lead, duplicates=(dup_b, dup_b2, dup_c))
    assert story.also_reported_by == ("b", "c")
