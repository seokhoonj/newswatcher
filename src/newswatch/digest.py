"""Assemble and send the digest email.

One email per poll: the new articles grouped by topic, each entry showing its title,
our LLM summary, and the source link — never the article's own text. Any selector
repairs the healer made this run are appended so the change is visible. Delivery is
mailmail's job (a base dependency); this module only renders the message and hands it
over, so 'how to send mail' lives in one place. mailmail is imported lazily so
importing this module does not pull it in until a send happens."""

from __future__ import annotations

from typing import Protocol, cast

from newswatch.errors import DigestError
from newswatch.stories import Story

__all__ = ["render_digest", "send_digest"]

_DIVIDER = "─" * 24


class _MailmailModule(Protocol):
    MailmailError: type[Exception]

    def send(self, *, subject: str, body: str, to: str, account: str | None = ...) -> object: ...


def render_digest(stories: tuple[Story, ...], *, heal_notes: tuple[str, ...] = ()
                  ) -> tuple[str, str]:
    """Render ``(subject, body)`` for the digest. Stories are grouped by topic in the
    order topics first appear; each entry is the lead's title / summary / link, with the
    other outlets that ran the same story noted under it. ``heal_notes`` are appended
    under a footer. An empty digest still renders (the caller decides whether to send)."""
    subject = f"[newswatch] {len(stories)} new stor{'y' if len(stories) == 1 else 'ies'}"
    if not stories:
        body = "No new articles this run."
    else:
        body = "\n\n".join(_render_group(topic, group)
                           for topic, group in _group_by_topic(stories))
    if heal_notes:
        body += ("\n\n" + _DIVIDER + "\nselector repairs:\n"
                 + "\n".join(f"- {note}" for note in heal_notes))
    return subject, body


def send_digest(
    stories: tuple[Story, ...], *, to: str, heal_notes: tuple[str, ...] = (),
    account: str | None = None,
) -> None:
    """Send the digest of ``stories`` to ``to`` (a mailmail address or address-book
    alias). A no-op when there is nothing to report and no heal notes.

    Raises:
        DigestError: mailmail is missing, or it refused or failed the send.
    """
    if not stories and not heal_notes:
        return
    subject, body = render_digest(stories, heal_notes=heal_notes)
    mailmail = _load_mailmail()
    try:
        mailmail.send(subject=subject, body=body, to=to, account=account)
    except mailmail.MailmailError as err:
        raise DigestError(f"could not send digest: {err}") from err
    except OSError as err:
        raise DigestError(f"network error sending digest: {err}") from err


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
    if story.duplicates:
        entry += f"\n  also reported by: {', '.join(story.also_reported_by)}"
    return entry


def _load_mailmail() -> _MailmailModule:
    try:
        import mailmail
    except ImportError as err:
        raise DigestError(
            "the mailmail package is required to send digests but could not be imported; "
            "reinstall newswatch"
        ) from err
    return cast(_MailmailModule, mailmail)
