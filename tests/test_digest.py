import newswatcher.digest as digest
from newswatcher.digest import render_digest, send_digest
from newswatcher.store import Article
from newswatcher.stories import Story


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

        def send(self, *, subject, body, to, html=None, account=None):
            sent.update(subject=subject, body=body, to=to)

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Fake())
    send_digest((_story("보험료 인상", "insurance", summary="요약문"),), email_to="you@e.com")
    assert sent["to"] == "you@e.com"
    assert "요약문" in sent["body"] and "https://e.com/x" in sent["body"]


def test_render_html_digest_is_a_full_document_grouped_by_topic():
    html = digest.render_html_digest(
        (_story("보험료 인상", "insurance", summary="요약문", link="https://e.com/x"),
         _story("은행 금리", "banking")))
    assert html.startswith("<!DOCTYPE html>")
    assert "보험료 인상" in html and "요약문" in html and "https://e.com/x" in html
    assert "insurance" in html and "banking" in html


def test_render_html_digest_notes_other_outlets():
    lead = _article("코스피 3000 돌파", "markets", link="https://a.com/1", source="yonhap")
    dup = _article("코스피 3000선 돌파", "markets", link="https://b.com/2", source="hankyung")
    html = digest.render_html_digest((Story(lead=lead, duplicates=(dup,)),))
    assert "also reported by: hankyung" in html


def test_render_html_digest_escapes_article_text():
    html = digest.render_html_digest((_story("A & B <script>", "t", summary="x < y"),))
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "x &lt; y" in html


def test_render_html_digest_escapes_outlet_names_and_heal_notes():
    # Every leaf that reaches the HTML must be escaped, not only the title/summary: an outlet name
    # and a heal note carry feed/heal text too. html.escape defaults to quote=True, so `"` also
    # becomes &quot;.
    lead = _article("T", "t", link="https://a.com/1", source="yonhap")
    dup = _article("d", "t", link="https://b.com/2", source='<Outlet & "Co">')
    html = digest.render_html_digest((Story(lead=lead, duplicates=(dup,)),),
                                     heal_notes=('<repair & "note">',))
    assert '&lt;Outlet &amp; &quot;Co&quot;&gt;' in html and "<Outlet" not in html
    assert '&lt;repair &amp; &quot;note&quot;&gt;' in html and "<repair" not in html


def test_render_html_digest_links_only_an_http_url():
    html = digest.render_html_digest((_story("Title", "t", link="https://e.com/x"),))
    assert '<a href="https://e.com/x"' in html   # a normal link is a real anchor


def test_render_html_digest_drops_a_dangerous_link_scheme():
    # html.escape neutralizes quotes but not the URL scheme, so a feed-supplied javascript:/data:
    # URL must not become a live href; the scheme is allowlisted to http(s) and the title falls
    # back to plain text (the standard link-target allowlist).
    for bad in ("javascript:alert(document.domain)", "data:text/html,<script>alert(1)</script>"):
        html = digest.render_html_digest((_story("Click me", "t", link=bad),))
        assert "javascript:" not in html and "data:text/html" not in html
        assert "Click me" in html   # still shown, just not as a link


def test_render_html_digest_survives_a_malformed_link_url():
    # urlsplit raises ValueError on unbalanced IPv6 brackets (http://[::1); the render must not
    # crash on semi-trusted feed input -- the link is treated as unsafe and the title is plain text.
    html = digest.render_html_digest((_story("Title", "t", link="http://[::1"),))
    assert "Title" in html                 # rendered, no crash
    assert "http://[::1" not in html       # the unparseable URL is not emitted as an href


def test_render_html_digest_escapes_quotes_in_title_and_summary():
    # html.escape(quote=True) also escapes " in element text; pin it for the title and summary
    # leaves too (not only outlet names / heal notes).
    html = digest.render_html_digest((_story('a "quoted" title', "t", summary='the "sum"'),))
    assert "&quot;quoted&quot;" in html and "&quot;sum&quot;" in html


def test_render_html_digest_empty_with_heal_notes():
    html = digest.render_html_digest((), heal_notes=("selector fixed",))
    assert "No new articles this run." in html
    assert "selector repairs" in html and "selector fixed" in html


def test_render_html_digest_omits_the_outlet_line_for_a_same_outlet_duplicate():
    # A duplicate from the SAME outlet as the lead leaves `also_reported_by` empty though
    # `duplicates` is truthy: the digest must not print a "also reported by:" line naming nobody.
    lead = _article("T", "t", link="https://a.com/1", source="yonhap")
    same = _article("T redux", "t", link="https://a.com/2", source="yonhap")
    story = (Story(lead=lead, duplicates=(same,)),)
    assert "also reported by" not in digest.render_html_digest(story)
    assert "also reported by" not in render_digest(story)[1]


def test_send_digest_passes_an_html_body_to_mailmail(monkeypatch):
    sent: dict[str, str] = {}

    class _Fake:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            sent.update(body=body, html=html or "")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Fake())
    send_digest((_story("보험료 인상", "insurance", summary="요약문"),), email_to="you@e.com")
    assert sent["html"].startswith("<!DOCTYPE html>")
    assert "보험료 인상" in sent["html"] and "요약문" in sent["html"]
    assert "요약문" in sent["body"]   # the plain-text fallback still carries the same content


def test_send_digest_hands_the_digest_to_pushpush_as_markdown(monkeypatch):
    sent: dict[str, str] = {}

    class _Fake:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            sent.update(text=text, to=to, markup=markup)

    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Fake())
    send_digest((_story("보험료 인상", "insurance", summary="요약문"),), push_to="alerts")
    assert sent["to"] == "alerts"
    assert sent["markup"] == "markdown"          # topic headers render as chat markdown
    assert "보험료 인상" in sent["text"] and "요약문" in sent["text"]


def test_send_digest_reaches_both_channels_when_both_are_given(monkeypatch):
    mailed: list[str] = []
    pushed: list[str] = []

    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            mailed.append(to)

    class _Push:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            pushed.append(to)

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Push())
    send_digest((_story("보험료 인상", "insurance"),), email_to="you@e.com", push_to="alerts")
    assert mailed == ["you@e.com"] and pushed == ["alerts"]


def test_send_digest_returns_a_partial_failure_without_raising(monkeypatch):
    # Email accepts the digest, chat is down: the chat failure comes back as a returned
    # message, not an exception -- so the caller advances its watermark and does not re-send
    # the email that already went out.
    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            pass

    class _Push:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            raise self.PushpushError("route revoked")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Push())
    failures = send_digest((_story("a", "t"),), email_to="you@e.com", push_to="alerts")
    assert len(failures) == 1 and "chat" in failures[0]


def test_send_digest_raises_only_when_every_channel_fails(monkeypatch):
    import pytest

    from newswatcher.errors import DigestError

    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            raise self.MailmailError("smtp down")

    class _Push:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            raise self.PushpushError("route revoked")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Push())
    with pytest.raises(DigestError):
        send_digest((_story("a", "t"),), email_to="you@e.com", push_to="alerts")


def test_send_digest_is_a_noop_when_nothing_to_report(monkeypatch):
    called = []
    monkeypatch.setattr(digest, "_load_mailmail", lambda: called.append(1))
    monkeypatch.setattr(digest, "_load_pushpush", lambda: called.append(1))
    result = send_digest((), email_to="you@e.com", push_to="alerts")
    assert called == []   # neither delivery package is even loaded
    assert result == ()   # the documented empty-tuple return


def test_send_digest_returns_empty_tuple_when_a_channel_accepts(monkeypatch):
    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            pass

    class _Push:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            pass

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Push())
    assert send_digest((_story("a", "t"),), email_to="you@e.com") == ()          # email-only
    assert send_digest((_story("a", "t"),), push_to="alerts") == ()              # chat-only
    assert send_digest((_story("a", "t"),), email_to="e@x", push_to="a") == ()   # both


def test_send_digest_noop_when_stories_present_but_no_destination(monkeypatch):
    # Stories exist but neither destination is given: nothing is sent, no delivery package loaded,
    # and the documented empty tuple comes back.
    called = []
    monkeypatch.setattr(digest, "_load_mailmail", lambda: called.append(1))
    monkeypatch.setattr(digest, "_load_pushpush", lambda: called.append(1))
    assert send_digest((_story("a", "t"),)) == ()
    assert called == []


def test_send_digest_returns_the_email_failure_when_chat_succeeds(monkeypatch):
    # The reverse of the existing partial-failure test: email is down, chat accepts -> the email
    # failure is returned (not raised), so chat is not re-sent on the next poll.
    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            raise self.MailmailError("smtp down")

    class _Push:
        PushpushError = RuntimeError

        def send(self, text, *, to, markup="plain"):
            pass

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "_load_pushpush", lambda: _Push())
    failures = send_digest((_story("a", "t"),), email_to="you@e.com", push_to="alerts")
    assert len(failures) == 1 and "email" in failures[0]


def test_send_digest_raises_when_the_only_channel_fails(monkeypatch):
    import pytest

    from newswatcher.errors import DigestError

    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            raise self.MailmailError("smtp down")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    with pytest.raises(DigestError):
        send_digest((_story("a", "t"),), email_to="you@e.com")   # single destination, all failed


def test_send_digest_funnels_a_raw_smtp_transport_error(monkeypatch):
    # mailmail's contract lets a raw smtplib.SMTPException through; it is an OSError subclass, so
    # the OSError branch funnels it to DigestError rather than letting it escape the send.
    import smtplib

    import pytest

    from newswatcher.errors import DigestError

    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            raise smtplib.SMTPServerDisconnected("connection dropped mid-send")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    with pytest.raises(DigestError):
        send_digest((_story("a", "t"),), email_to="you@e.com")


def test_send_digest_funnels_a_too_old_mailmail(monkeypatch):
    # mailmail present but missing HTMLLayout -> render_html_digest raises ImportError inside the
    # send; it must funnel to DigestError, not escape as a raw ImportError that crashes the poll.
    import pytest

    from newswatcher.errors import DigestError

    class _Mail:
        MailmailError = RuntimeError

        def send(self, *, subject, body, to, html=None, account=None):
            pass

    def _too_old(*a, **k):
        raise ImportError("cannot import name 'HTMLLayout' from 'mailmail'")

    monkeypatch.setattr(digest, "_load_mailmail", lambda: _Mail())
    monkeypatch.setattr(digest, "render_html_digest", _too_old)
    with pytest.raises(DigestError):
        send_digest((_story("a", "t"),), email_to="you@e.com")


def test_send_digest_reports_the_missing_email_extra(monkeypatch):
    # email delivery without newswatcher[email]: the absent mailmail import funnels to a DigestError
    # that names the extra to install, rather than escaping as a raw ImportError.
    import sys

    import pytest

    from newswatcher.errors import DigestError

    monkeypatch.setitem(sys.modules, "mailmail", None)   # `import mailmail` raises ImportError
    with pytest.raises(DigestError, match=r"newswatcher\[email\]"):
        send_digest((_story("a", "t"),), email_to="you@e.com")


def test_send_digest_reports_the_missing_chat_extra(monkeypatch):
    import sys

    import pytest

    from newswatcher.errors import DigestError

    monkeypatch.setitem(sys.modules, "pushpush", None)
    with pytest.raises(DigestError, match=r"newswatcher\[chat\]"):
        send_digest((_story("a", "t"),), push_to="alerts")
