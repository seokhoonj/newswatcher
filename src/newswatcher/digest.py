"""Assemble and send the digest.

One digest per poll: the new stories grouped by topic, each entry showing the lead's
title, our LLM summary, and the source link — never the article's own text. Any selector
repairs the healer made this run are appended so the change is visible. This module
renders the message once and hands it to a delivery package — mailmail for email,
pushpush for chat, both base dependencies — so 'how to send' lives in one place per
channel. Each is imported lazily, so importing this module pulls in neither until a send
on that channel happens."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Literal, Protocol, cast
from urllib.parse import urlsplit

from newswatcher.errors import DigestError
from newswatcher.stories import Story

if TYPE_CHECKING:
    from mailmail import HTMLLayout

__all__ = ["render_digest", "render_html_digest", "send_digest"]

_DIVIDER = "─" * 24


class _MailmailModule(Protocol):
    MailmailError: type[Exception]

    def send(self, *, subject: str, body: str, to: str, html: str | None = ...,
             account: str | None = ...) -> object: ...


class _PushpushModule(Protocol):
    PushpushError: type[Exception]

    def send(self, text: str, *, to: str,
             markup: Literal["plain", "markdown", "html"] = ...) -> object: ...


def render_digest(stories: tuple[Story, ...], *, heal_notes: tuple[str, ...] = ()
                  ) -> tuple[str, str]:
    """Render ``(subject, body)`` for the digest. Stories are grouped by topic in the
    order topics first appear; each entry is the lead's title / summary / link, with the
    other outlets that ran the same story noted under it. ``heal_notes`` are appended
    under a footer. An empty digest still renders (the caller decides whether to send)."""
    subject = f"[newswatcher] {len(stories)} new stor{'y' if len(stories) == 1 else 'ies'}"
    if not stories:
        body = "No new articles this run."
    else:
        body = "\n\n".join(_render_group(topic, group)
                           for topic, group in _group_by_topic(stories))
    if heal_notes:
        body += ("\n\n" + _DIVIDER + "\nselector repairs:\n"
                 + "\n".join(f"- {note}" for note in heal_notes))
    return subject, body


def render_html_digest(stories: tuple[Story, ...], *, heal_notes: tuple[str, ...] = ()) -> str:
    """Render the digest as a standalone HTML document for an email body, built with mailmail's
    themed ``HTMLLayout`` -- so the digest wears the same house style mailmail gives every
    message. Stories are grouped by topic exactly as ``render_digest``; each entry is the lead's
    linked title, our summary, and the outlets that ran the same story. This is the email path
    only: chat carries no HTML (the plain-text body holds the same content)."""
    from mailmail import HTMLLayout

    layout = HTMLLayout()
    html_parts = [layout.header(eyebrow="newswatcher", title=_headline(len(stories)))]
    if not stories:
        html_parts.append(layout.para_row(escape("No new articles this run.")))
    else:
        for topic, group in _group_by_topic(stories):
            html_parts.append(layout.section(f"{topic} ({len(group)})"))
            html_parts.extend(layout.para_row(_story_html(layout, story)) for story in group)
    if heal_notes:
        html_parts.append(layout.section("selector repairs"))
        html_parts.append(layout.para_row("<br>".join(escape(note) for note in heal_notes)))
    return layout.render_page(html_parts)


def _headline(count: int) -> str:
    """The digest's one-line count, e.g. ``"3 new stories"`` -- the header title (the eyebrow
    already carries the newswatcher name)."""
    return f"{count} new stor{'y' if count == 1 else 'ies'}"


def _story_html(layout: HTMLLayout, story: Story) -> str:
    """One story as an HTML paragraph fragment: the lead's linked title, its summary, and --
    when *another* outlet ran the same story -- who else did. Leaf text is escaped; the layout's
    own theme colors the title link. The title is a link only when the feed's URL is ``http(s)``:
    ``html.escape`` neutralizes quotes but not the URL scheme, so an off-allowlist scheme falls
    back to plain text."""
    lead = story.lead
    escaped_title = escape(lead.title)
    if _is_safe_url(lead.link):
        title = (f'<a href="{escape(lead.link, quote=True)}" '
                 f'style="color:{layout.theme.heading_color};font-weight:700;'
                 f'text-decoration:none;">{escaped_title}</a>')
    else:
        title = escaped_title
    html_lines = [title, escape(lead.summary)]
    if story.also_reported_by:   # excludes the lead's own outlet, so guard on it, not `duplicates`
        html_lines.append("also reported by: " + escape(", ".join(story.also_reported_by)))
    return "<br>".join(html_lines)


def _is_safe_url(url: str) -> bool:
    """Whether ``url`` may be placed in an ``href`` -- an ``http`` or ``https`` scheme only. A
    feed-supplied ``javascript:`` or ``data:`` URL survives ``html.escape`` (which touches quotes,
    not the scheme) as a live link, so it is the scheme, not the escaping, that has to be checked --
    the same allowlist bleach, sanitize-html, and feedparser apply to a link target."""
    return urlsplit(url).scheme in ("http", "https")


def send_digest(
    stories: tuple[Story, ...], *, email_to: str | None = None, push_to: str | None = None,
    heal_notes: tuple[str, ...] = (), account: str | None = None,
) -> tuple[str, ...]:
    """Send the digest of ``stories`` to each destination given: ``email_to`` (a mailmail
    address or address-book alias) via email, ``push_to`` (a pushpush route name) via chat,
    or both. A no-op when there is nothing to report and no heal notes, or when neither
    destination is given -- the caller decides which channels are configured.

    Returns the delivery failures, one message each -- empty when every configured
    destination accepted the digest. A caller that persists progress only on success can
    still do so on a *partial* failure, because the channels that did accept the digest
    must not be re-sent. The failed channel's copy of *this* digest is therefore dropped,
    not queued for retry -- a later poll reaches it only with newer stories.

    Raises:
        DigestError: only when *every* configured destination failed. A caller that re-sends
            on a raise (having withheld its watermark) then re-sends nothing that already
            went out; a partial failure is returned, not raised, for the same reason -- the
            delivered channel would otherwise get the digest twice on the retry.
    """
    if not stories and not heal_notes:
        return ()
    subject, body = render_digest(stories, heal_notes=heal_notes)
    failures: list[str] = []
    delivered = 0
    if email_to:
        try:
            _send_email(subject, body, stories, heal_notes, to=email_to, account=account)
            delivered += 1
        except DigestError as err:
            failures.append(str(err))
    if push_to:
        try:
            _send_chat(subject, body, to=push_to)
            delivered += 1
        except DigestError as err:
            failures.append(str(err))
    if (email_to or push_to) and not delivered:
        raise DigestError("; ".join(failures))
    return tuple(failures)


def _send_email(subject: str, body: str, stories: tuple[Story, ...],
                heal_notes: tuple[str, ...], *, to: str, account: str | None) -> None:
    mailmail = _load_mailmail()
    try:
        # Build the rich body inside the try so a too-old mailmail (no HTMLLayout) is funneled to a
        # DigestError like any other send failure, not raised as a bare ImportError past the caller.
        html = render_html_digest(stories, heal_notes=heal_notes)   # body is the text fallback
        mailmail.send(subject=subject, body=body, to=to, html=html, account=account)
    except mailmail.MailmailError as err:
        raise DigestError(f"could not send digest email: {err}") from err
    except OSError as err:
        # mailmail's contract lets a raw transport error through -- and smtplib.SMTPException is
        # itself an OSError subclass, so this one catch funnels an SMTP disconnect and a network
        # error alike into the delivery-failure surface.
        raise DigestError(f"network error sending digest email: {err}") from err
    except ImportError as err:
        raise DigestError(
            f"the installed mailmail is too old to render the digest: {err}; upgrade mailmail"
        ) from err


def _send_chat(subject: str, body: str, *, to: str) -> None:
    """Deliver to a pushpush route. Chat has no subject line, so the subject leads the text;
    the body is the same markdown the email carries, so the topic headers render as chat
    markdown."""
    pushpush = _load_pushpush()
    try:
        pushpush.send(f"{subject}\n\n{body}", to=to, markup="markdown")
    except pushpush.PushpushError as err:
        raise DigestError(f"could not send digest to chat: {err}") from err
    except OSError as err:
        raise DigestError(f"network error sending digest to chat: {err}") from err


def _group_by_topic(stories: tuple[Story, ...]) -> list[tuple[str, list[Story]]]:
    """Group stories by their lead's first topic tag, preserving first-appearance order. A
    lead tagged with several topics is listed under its first tag only, so the digest does
    not repeat it."""
    stories_by_topic: dict[str, list[Story]] = {}
    for story in stories:
        key = story.lead.topics[0] if story.lead.topics else "(untagged)"
        stories_by_topic.setdefault(key, []).append(story)
    return list(stories_by_topic.items())


def _render_group(topic: str, stories: list[Story]) -> str:
    header = f"## {topic} ({len(stories)})"
    entries = "\n\n".join(_render_story(story) for story in stories)
    return f"{header}\n\n{entries}"


def _render_story(story: Story) -> str:
    """One digest entry: the lead's title / summary / link, and -- when other outlets ran
    the same story -- a line naming them under it."""
    lead = story.lead
    entry = f"- {lead.title}\n  {lead.summary}\n  {lead.link}"
    if story.also_reported_by:   # excludes the lead's own outlet, so guard on it, not `duplicates`
        entry += f"\n  also reported by: {', '.join(story.also_reported_by)}"
    return entry


def _load_mailmail() -> _MailmailModule:
    try:
        import mailmail
    except ImportError as err:
        # Funnel any import failure -- the package absent OR a broken sub-dependency -- to
        # DigestError, so a send never escapes as a raw ImportError past the caller. The message
        # stays generic rather than claiming "not installed", which a sub-dependency failure is not.
        raise DigestError(
            f"the mailmail package could not be imported ({err}); "
            f"reinstall or repair newswatcher's dependencies"
        ) from err
    return cast(_MailmailModule, mailmail)


def _load_pushpush() -> _PushpushModule:
    try:
        import pushpush
    except ImportError as err:
        raise DigestError(
            f"the pushpush package could not be imported ({err}); "
            f"reinstall or repair newswatcher's dependencies"
        ) from err
    return cast(_PushpushModule, pushpush)
