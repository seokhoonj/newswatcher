from newswatch.digest import render_digest
from newswatch.store import Article


def _article(title, topic, link="https://e.com/x", summary="요약문"):
    return Article(guid=link, title=title, link=link, source_name="s",
                   published="2026-08-15T00:00:00Z", topics=(topic,),
                   summary=summary, summary_model="m")


def test_render_groups_by_topic():
    arts = (_article("보험료 인상", "insurance"),
            _article("은행 금리", "banking"),
            _article("손해율 급등", "insurance"))
    subject, body = render_digest(arts)
    assert "3" in subject  # count in subject
    assert "insurance" in body and "banking" in body
    # each entry shows title, summary, link — never a body field (there is none)
    assert "보험료 인상" in body and "요약문" in body and "https://e.com/x" in body
    # insurance section lists its two before banking's one (insertion order of topics)
    assert body.index("insurance") < body.index("banking")


def test_heal_notes_appended():
    subject, body = render_digest((_article("a", "insurance"),),
                                  heal_notes=("repaired 'x' selectors (item: 'old' -> 'new')",))
    assert "repaired 'x'" in body


def test_empty_digest_has_stable_subject():
    subject, body = render_digest(())
    assert isinstance(subject, str) and subject
