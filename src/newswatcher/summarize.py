"""Write a short original summary of an article with an LLM.

The summary is what newswatcher archives and emails -- never the article's own text --
so it is original prose, not a copy of the source. It runs on thinchat (see
``_llm``); the body is the summary's input and is discarded after. When the body
could not be fetched, the feed's own title and summary are used instead, so an
article is never dropped for lack of a body."""

from __future__ import annotations

from dataclasses import dataclass

from thinchat.errors import ThinchatError

from newswatcher._llm import DEFAULT_PROVIDER, make_llm_client
from newswatcher.categories import Category
from newswatcher.errors import LLMError
from newswatcher.feed import FeedItem

__all__ = ["Summary", "summarize_article"]

_MAX_TOKENS = 320            # summary only -- the default, unchanged when classification is off
_CLASSIFY_MAX_TOKENS = 360   # summary plus a leading category line, only when classifying
_SYSTEM = (
    "You summarize a news article in two or three plain sentences, in the article's "
    "own language. Write original prose; do not copy sentences verbatim. No preamble."
)
_SYSTEM_CLASSIFY = (
    _SYSTEM + " Before the summary, classify the article into exactly one of the categories"
    " you are given, by its name. Reply with the category name alone on the first line, then"
    " a blank line, then the summary. If none of the categories fit, use the last one."
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Summary:
    """One article's LLM summary: our original ``text``, which ``model`` produced it, and
    the ``category`` the model classified it into ("" when no categories were supplied, or
    the reply did not name a known category in the required layout). The article's own
    title and link travel with the ``FeedItem``, not here."""

    text:     str
    model:    str
    category: str = ""


def summarize_article(
    item: FeedItem, body: str, *, provider: str = DEFAULT_PROVIDER,
    model: str | None = None, api_key: str | None = None,
    categories: tuple[Category, ...] = (),
) -> Summary:
    """Summarize ``item`` from its ``body`` (or, when body is empty, from the feed's
    title + summary). Returns our original summary text, the model that wrote it, and --
    when ``categories`` are supplied -- the single category the model classified it into
    (in the same call, so no extra request; "" when the reply names no known category).

    Raises:
        LLMError: the provider is unknown, no key is available, the call failed, or it
            returned an empty reply.
    """
    source_text = body.strip() or f"{item.title}\n\n{item.summary}".strip()
    system = _SYSTEM_CLASSIFY if categories else _SYSTEM
    prompt = f"Title: {item.title}\n\n{source_text}"
    if categories:
        prompt = f"Categories:\n{_format_categories(categories)}\n\n{prompt}"
    max_tokens = _CLASSIFY_MAX_TOKENS if categories else _MAX_TOKENS   # classify-off stays at 320
    with make_llm_client(provider, model=model, api_key=api_key,
                        max_tokens=max_tokens, action="summarizing") as client:
        try:
            reply = client.complete(prompt, system=system).strip()
            resolved_model = client.model   # the model actually used; read before the client closes
        except ThinchatError as err:
            # thinchat scrubs any provider key from its own error and the chain beneath it, so
            # the message is safe to interpolate as-is.
            raise LLMError(f"summary request failed: {err}") from err
    category, text = _split_category(reply, categories)
    if not text:
        raise LLMError("summary request returned an empty reply")
    return Summary(text=text, model=resolved_model, category=category)


def _format_categories(categories: tuple[Category, ...]) -> str:
    """Format the category list for the prompt: one ``- name: hint`` line each."""
    return "\n".join(f"- {category.name}: {category.hint}" if category.hint else f"- {category.name}"
                     for category in categories)


def _split_category(reply: str, categories: tuple[Category, ...]) -> tuple[str, str]:
    """Peel a leading category line off ``reply`` when categories were requested.

    Returns ``(category, summary)``. The line is peeled only when it matches a category
    name AND the requested "name, blank line, summary" layout holds (the name is the whole
    reply, or a blank line follows it), so a summary whose own first line happens to equal
    a category name is not truncated. When no categories were requested, or the layout does
    not hold, the category is "" and the whole reply is the summary -- a model that ignores
    the format still yields a usable summary."""
    if not categories:
        return "", reply
    reply = reply.replace("\r\n", "\n").replace("\r", "\n")   # tolerate CRLF-style line endings
    category_name_by_normalized = {category.name.strip().lower(): category.name
                                   for category in categories}
    first_line, _, remainder = reply.partition("\n")
    matched_name = category_name_by_normalized.get(first_line.strip().lower())
    if matched_name is None:
        return "", reply
    if remainder and not remainder.lstrip(" \t").startswith("\n"):   # no blank line after the name:
        return "", reply                                            # not the classify layout, keep it whole
    return matched_name, remainder.strip()
