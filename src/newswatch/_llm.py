"""Build a thinchat LLM client with its key resolved from the environment or the
credentials file.

newswatch's LLM tasks -- summarizing an article, repairing a broken crawl selector --
run on the thinchat library, which speaks to every provider behind one interface.
Keys come from the provider's standard environment variable, or from newswatch's
``credentials.json`` when the variable is unset. Gemini's free tier is the default
backend for the light summary task."""

from __future__ import annotations

from thinchat import PROVIDERS, Client, make_client
from thinchat.errors import ThinchatError
from thinchat.keys import ENV_BY_PROVIDER

from newswatch import credentials
from newswatch.errors import LLMError, NewswatchError

__all__ = ["DEFAULT_PROVIDER", "make_llm_client", "scrub_secrets"]

DEFAULT_PROVIDER = "gemini"
_MAX_RETRIES = 6


def scrub_secrets(text: str) -> str:
    """Replace any resolvable provider key found in ``text`` with ``"***"``.

    A provider library's exception message can carry the API key -- Gemini, the default,
    sends the key as a URL query parameter, so an HTTP error string embeds it. newswatch
    interpolates such messages into its own errors and logs, so it scrubs the key first
    rather than trusting the library not to include it. Best-effort: it consults the same
    keys ``make_llm_client`` would use, and a credentials-file problem while scrubbing is
    swallowed so the original error still surfaces.
    """
    for env_name in ENV_BY_PROVIDER.values():
        try:
            key = credentials.secret(env_name)
        except NewswatchError:
            continue
        if key and key in text:
            text = text.replace(key, "***")
    return text


def make_llm_client(
    provider: str = DEFAULT_PROVIDER, *, model: str | None = None,
    api_key: str | None = None, max_tokens: int, action: str,
) -> Client:
    """Build the thinchat client for ``provider``. The key comes from ``api_key`` when
    given, else the provider's standard env var, else newswatch's ``credentials.json``;
    ``model`` overrides the default; ``max_tokens`` caps the reply; ``action`` names the
    caller in the missing-key message.

    Raises:
        LLMError: unknown provider, no API key available for it, or the client could
            not be constructed.
        ConfigError: newswatch's ``credentials.json`` is present but unreadable, not JSON,
            or not a JSON object (propagated from ``credentials.secret``).
    """
    if provider not in PROVIDERS:
        raise LLMError(f"unknown LLM provider {provider!r}; choose one of {', '.join(PROVIDERS)}")
    env_name = ENV_BY_PROVIDER.get(provider)
    key = api_key if api_key is not None else (credentials.secret(env_name) if env_name else None)
    if env_name is not None and not key:
        raise LLMError(
            f"{action} needs an API key for {provider}; set {env_name} "
            f'or add "{env_name}" to newswatch\'s credentials.json'
        )
    try:
        return make_client(provider, model=model, api_key=key,
                           max_tokens=max_tokens, max_retries=_MAX_RETRIES)
    except ThinchatError as err:
        raise LLMError(f"{action} could not start {provider}: {scrub_secrets(str(err))}") from err
