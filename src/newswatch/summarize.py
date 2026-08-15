"""Write a short original summary of an article with an LLM.

The summary is what newswatch archives and emails -- never the article's own text --
so it is original prose, not a copy of the source. It runs on thinchat (see
``_llm``); the body is the summary's input and is discarded after. When the body
could not be fetched, the feed's own title and summary are used instead, so an
article is never dropped for lack of a body."""

from __future__ import annotations

from dataclasses import dataclass

from thinchat.errors import ThinchatError

from newswatch._llm import DEFAULT_PROVIDER, make_llm_client
from newswatch.errors import LLMError
from newswatch.feed import FeedItem

__all__ = ["Summary", "summarize_article"]

_MAX_TOKENS = 320
_SYSTEM = (
    "You summarize a news article in two or three plain sentences, in the article's "
    "own language. Write original prose; do not copy sentences verbatim. No preamble."
)


@dataclass(frozen=True, slots=True)
class Summary:
    """One article's LLM summary: the ``title`` and ``link`` carried through for the
    digest, our ``text``, and which ``model`` produced it."""

    title: str
    link:  str
    text:  str
    model: str


def summarize_article(
    item: FeedItem, body: str, *, provider: str = DEFAULT_PROVIDER,
    model: str | None = None, api_key: str | None = None,
) -> Summary:
    """Summarize ``item`` from its ``body`` (or, when body is empty, from the feed's
    title + summary). Returns our original summary paired with the item's title/link.

    Raises:
        LLMError: the provider is unknown, no key is available, the call failed, or it
            returned an empty reply.
    """
    source_text = body.strip() or f"{item.title}\n\n{item.summary}".strip()
    prompt = f"Title: {item.title}\n\n{source_text}"
    with make_llm_client(provider, model=model, api_key=api_key,
                        max_tokens=_MAX_TOKENS, action="summarizing") as client:
        try:
            text = client.complete(prompt, system=_SYSTEM).strip()
        except ThinchatError as err:
            raise LLMError(f"summary request failed: {err}") from err
    if not text:
        raise LLMError("summary request returned an empty reply")
    return Summary(title=item.title, link=item.link, text=text, model=client.model)
