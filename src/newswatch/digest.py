"""Assemble and send the digest email.

One email per poll: the new articles grouped by topic, each entry showing its title,
our LLM summary, and the source link — never the article's own text. Any selector
repairs the healer made this run are appended so the change is visible. Delivery is
mailmail's job (a base dependency); this module only renders the message and hands it
over, so 'how to send mail' lives in one place. mailmail is imported lazily so
importing this module does not pull it in until a send happens."""

from __future__ import annotations

from typing import Protocol, cast

from newswatch.errors import NotifyError
from newswatch.store import Article

__all__ = ["render_digest", "send_digest"]

_DIVIDER = "─" * 24


class _MailmailModule(Protocol):
    MailmailError: type[Exception]

    def send(self, *, subject: str, body: str, to: object, account: str | None = ...) -> object: ...


def render_digest(articles: tuple[Article, ...], *, heal_notes: tuple[str, ...] = ()
                  ) -> tuple[str, str]:
    """Render ``(subject, body)`` for the digest. Articles are grouped by topic in the
    order topics first appear; each entry is title / summary / link. ``heal_notes`` are
    appended under a footer. An empty digest still renders (the caller decides whether
    to send)."""
    subject = f"[newswatch] {len(articles)} new article(s)"
    if not articles:
        body = "No new articles this run."
    else:
        body = "\n\n".join(_render_group(topic, group)
                           for topic, group in _group_by_topic(articles))
    if heal_notes:
        body += "\n\n" + _DIVIDER + "\nselector repairs:\n" + "\n".join(f"- {n}" for n in heal_notes)
    return subject, body


def send_digest(
    articles: tuple[Article, ...], *, to: object, heal_notes: tuple[str, ...] = (),
    account: str | None = None,
) -> None:
    """Send the digest of ``articles`` to ``to`` (a mailmail address or address-book
    alias). A no-op when there is nothing to report and no heal notes.

    Raises:
        NotifyError: mailmail is missing, or it refused or failed the send.
    """
    if not articles and not heal_notes:
        return
    subject, body = render_digest(articles, heal_notes=heal_notes)
    mailmail = _load_mailmail()
    try:
        mailmail.send(subject=subject, body=body, to=to, account=account)
    except mailmail.MailmailError as err:
        raise NotifyError(f"could not send digest: {err}") from err
    except OSError as err:
        raise NotifyError(f"network error sending digest: {err}") from err


def _group_by_topic(articles: tuple[Article, ...]) -> list[tuple[str, list[Article]]]:
    """Group articles by their first topic tag, preserving first-appearance order. An
    article tagged with several topics is listed under its first tag only, so the
    digest does not repeat it."""
    groups: dict[str, list[Article]] = {}
    for article in articles:
        key = article.topics[0] if article.topics else "(untagged)"
        groups.setdefault(key, []).append(article)
    return list(groups.items())


def _render_group(topic: str, articles: list[Article]) -> str:
    header = f"## {topic} ({len(articles)})"
    entries = "\n\n".join(
        f"- {a.title}\n  {a.summary}\n  {a.link}" for a in articles
    )
    return f"{header}\n\n{entries}"


def _load_mailmail() -> _MailmailModule:
    try:
        import mailmail
    except ImportError as err:
        raise NotifyError(
            "the mailmail package is required to send digests but could not be imported; "
            "reinstall newswatch"
        ) from err
    return cast(_MailmailModule, mailmail)
