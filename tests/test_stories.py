import math

from newswatcher.store import Article
from newswatcher.stories import Story, group_stories, title_similarity


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


def test_titles_that_normalize_to_empty_are_never_similar():
    # All-punctuation headlines normalize to "" -- no bigrams and no exact-match value, so
    # two unrelated punctuation-only titles must not collapse into one story.
    assert title_similarity("!!!", "???") == 0.0
    assert title_similarity("...", "...") == 0.0


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
    # A REAL transitive chain: a~b and b~c both meet the threshold, but a and c do not.
    # Greedy leader compares each article only to existing LEADS, so c (unlike b) does not
    # get pulled into a's story via the b link -- a transitive-clustering impl would wrongly
    # merge all three. (Asserting the three similarities up front so the chain is explicit.)
    a = _article("금리 인상 우려 확산")
    b = _article("인상 우려 확산 전망")
    c = _article("우려 확산 전망 발표")
    assert title_similarity(a.title, b.title) >= 0.5   # a ~ b
    assert title_similarity(b.title, c.title) >= 0.5   # b ~ c
    assert title_similarity(a.title, c.title) < 0.5    # a NOT ~ c
    stories = group_stories((a, b, c))
    assert stories[0].lead is a and b in stories[0].duplicates
    assert stories[-1].lead is c and stories[-1].duplicates == ()


def test_group_stories_merges_at_the_exact_threshold_and_separates_just_above():
    # The join test is `>=`, so a pair whose score is exactly the threshold merges, and the
    # smallest step above it separates. (Score computed, not hardcoded, so it stays true.)
    a = _article("코스피 3000 돌파")
    b = _article("코스피, 3000선 돌파")
    score = title_similarity(a.title, b.title)
    assert len(group_stories((a, b), threshold=score)) == 1
    assert len(group_stories((a, b), threshold=math.nextafter(score, 1.0))) == 2


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
