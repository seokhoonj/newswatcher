"""Build a thinchat LLM client with its key resolved from the environment or the
credentials file.

newswatcher's LLM tasks -- summarizing an article, repairing a broken crawl selector --
run on the thinchat library, which speaks to every provider behind one interface.
Keys come from the provider's standard environment variable, or from newswatcher's
``credentials.json`` when the variable is unset. Gemini's free tier is the default
backend for the light summary task."""

from __future__ import annotations

from typing import Any

from thinchat import PROVIDERS, Client, make_client
from thinchat.errors import ThinchatError
from thinchat.keys import ENV_BY_PROVIDER

from newswatcher import credentials
from newswatcher.errors import ConfigError, LLMError

__all__ = ["DEFAULT_PROVIDER", "PROVIDERS", "make_llm_client", "scrub_secrets",
           "scrub_exception", "validate_provider"]

DEFAULT_PROVIDER = "gemini"
_MAX_RETRIES = 6


def validate_provider(provider: str) -> None:
    """Check that ``provider`` is a backend thinchat knows -- the single home for this
    check, so the CLI's early validation and ``make_llm_client`` give the same message.

    Raises:
        LLMError: the provider is not a known backend.
    """
    if provider not in PROVIDERS:
        raise LLMError(
            f"unknown LLM provider {provider!r}; choose one of {', '.join(sorted(PROVIDERS))}")


def scrub_secrets(text: str, *, extra_key: str | None = None) -> str:
    """Replace any provider key found in ``text`` with ``"***"``.

    A provider library's exception message can carry the API key -- Gemini, the default,
    sends the key as a URL query parameter, so an HTTP error string embeds it. newswatcher
    interpolates such messages into its own errors and logs, so it scrubs the key first
    rather than trusting the library not to include it. It redacts the keys
    ``make_llm_client`` would resolve from the environment / credentials file, plus
    ``extra_key`` when given -- an explicitly-passed ``api_key`` is not in either store, so
    a caller must name it here for it to be scrubbed. Best-effort: a credentials-file
    problem while scrubbing is swallowed so the original error still surfaces.
    """
    keys = []
    for env_name in ENV_BY_PROVIDER.values():
        try:
            resolved = credentials.secret(env_name)
        except ConfigError:
            continue
        if resolved:
            keys.append(resolved)
    if extra_key:
        keys.append(extra_key)
    for key in keys:
        if key in text:
            text = text.replace(key, "***")
    return text


def scrub_exception(err: BaseException, *, extra_key: str | None = None) -> BaseException:
    """Scrub any resolvable provider key from ``err`` and its whole ``__cause__`` /
    ``__context__`` chain, in place, then return ``err``.

    ``scrub_secrets`` only cleans the message we build; a caller that does
    ``logging.exception`` (or lets the error propagate to a traceback) prints the entire
    chained cause, where a provider library -- or the transport error beneath it, which
    Gemini spells with the key in a URL query -- still carries the raw key. Walking the
    chain and rewriting each exception's ``args`` (the source of ``str()`` and the
    traceback) plus the ``url`` attribute a transport error attaches (``err.request.url`` /
    ``err.response.url``, where Gemini's key lives) covers the standard renderings; a caller
    that reads some other custom attribute directly is on its own. Returns ``err`` so it
    reads as ``raise LLMError(...) from scrub_exception(err)``.
    """
    seen: set[int] = set()
    node: BaseException | None = err
    while node is not None and id(node) not in seen:
        seen.add(id(node))
        try:
            if node.args:
                node.args = tuple(
                    scrub_secrets(a, extra_key=extra_key) if isinstance(a, str) else a
                    for a in node.args)
        except Exception:
            pass   # a subclass whose args read/set raises -- other links are still scrubbed
        # A transport error carries the fetched URL -- and thus a query-string key -- on the
        # exception and on its .request/.response; scrub those too, best-effort. Every access
        # is wrapped: httpx (anthropic/openai backends) spells .request as a property that
        # *raises* RuntimeError when unset, not return None, and this scrubber runs on the
        # error path -- if it raised it would mask the very error it was cleaning.
        url_holders: list[Any] = [node]
        for attr in ("request", "response"):
            try:
                url_holders.append(getattr(node, attr, None))
            except Exception:
                url_holders.append(None)
        for holder in url_holders:
            try:
                raw_url = getattr(holder, "url", None)
            except Exception:
                continue   # a url property that raises when unset -- nothing to scrub here
            if not isinstance(raw_url, str):
                continue
            try:
                holder.url = scrub_secrets(raw_url, extra_key=extra_key)
            except Exception:
                pass   # a read-only or raising url property -- args/message are still redacted
        try:
            node = node.__cause__ or node.__context__
        except Exception:
            node = None   # a subclass whose __cause__/__context__ raises ends the walk here
    return err


def make_llm_client(
    provider: str = DEFAULT_PROVIDER, *, model: str | None = None,
    api_key: str | None = None, max_tokens: int, action: str,
) -> Client:
    """Build the thinchat client for ``provider``. The key comes from ``api_key`` when
    given, else the provider's standard env var, else newswatcher's ``credentials.json``;
    ``model`` overrides the default; ``max_tokens`` caps the reply; ``action`` names the
    caller in the missing-key message.

    Raises:
        LLMError: unknown provider, no API key available for it, or the client could
            not be constructed.
        ConfigError: newswatcher's ``credentials.json`` is present but unreadable, not JSON,
            or not a JSON object (propagated from ``credentials.secret``).
    """
    validate_provider(provider)
    env_name = ENV_BY_PROVIDER.get(provider)
    key = api_key if api_key is not None else (credentials.secret(env_name) if env_name else None)
    if env_name is not None and not key:
        raise LLMError(
            f"{action} needs an API key for {provider}; set {env_name} "
            f'or add "{env_name}" to newswatcher\'s credentials.json'
        )
    try:
        return make_client(provider, model=model, api_key=key,
                           max_tokens=max_tokens, max_retries=_MAX_RETRIES)
    except ThinchatError as err:
        raise LLMError(
            f"{action} could not start {provider}: {scrub_secrets(str(err), extra_key=key)}"
        ) from scrub_exception(err, extra_key=key)
