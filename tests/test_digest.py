import newswatch.digest as digest
from newswatch.digest import render_digest, send_digest
from newswatch.store import Article
from newswatch.stories import Story


def _article(title, topic, link="https://e.com/x", summary="요약문", source="s"):
    return Article(guid=link, title=title, link=link, source_name=source,
                   published="2026-08-15T00:00:00Z", topics=(topic,),
                   summary=summary, summary_model="m")


def _story(title, topic, **kwargs):
    return Story(lead=_article(title, topic, **kwargs))


def test_render_groups_by_topic():
    stories = (_story("보험료 인상", "insurance"),
               _story("은행 금리", "banking"),
               _story("손해율 급등", "insurance"))
    subject, body = render_digest(stories)
    assert "3" in subject  # count in subject
    assert "insurance" in body and "banking" in body
    # each entry shows title, summary, link — never a body field (there is none)
    assert "보험료 인상" in body and "요약문" in body and "https://e.com/x" in body
    # insurance section lists its two before banking's one (insertion order of topics)
    assert body.index("insurance") < body.index("banking")


def test_render_notes_the_other_outlets_under_a_duplicated_story():
    lead = _article("코스피 3000 돌파", "markets", link="https://a.com/1", source="yonhap")
    dup = _article("코스피 3000선 돌파", "markets", link="https://b.com/2", source="hankyung")
    subject, body = render_digest((Story(lead=lead, duplicates=(dup,)),))
    assert "1 new story" in subject          # one story, not two articles
    assert "코스피 3000 돌파" in body         # the lead's title, once
    assert "also reported by: hankyung" in body
    assert "https://b.com/2" not in body     # the duplicate's own link is not repeated


def test_heal_notes_appended():
    subject, body = render_digest((_story("a", "insurance"),),
                                  heal_notes=("repaired 'x' selectors (item: 'old' -> 'new')",))
    assert "repaired 'x'" in body


def test_empty_digest_has_stable_subject():
    subject, body = render_digest(())
    assert isinstance(subject, str) and subject


def test_archive_and_digest_carry_no_body():
    # The no-body guarantee is structural: an Article has no body field, so neither the
    # archive nor the digest can carry the publisher's text.
    assert "body" not in Article.__dataclass_fields__


def test_send_digest_hands_summary_and_link_to_mailmail(monkeypatch):
    sent: dict[str, str] = {}

    class _Fake:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, account=None):
            sent.update(subject=subject, body=body, to=to)

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Fake())
    send_digest((_story("보험료 인상", "insurance", summary="요약문"),), to="you@e.com")
    assert sent["to"] == "you@e.com"
    assert "요약문" in sent["body"] and "https://e.com/x" in sent["body"]


def test_send_digest_is_a_noop_when_nothing_to_report(monkeypatch):
    called = []
    monkeypatch.setattr(digest, "_load_mailmail", lambda: called.append(1))
    send_digest((), to="you@e.com")
    assert called == []   # mailmail is never even loaded
