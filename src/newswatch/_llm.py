"""Build a thinchat LLM client with its key resolved from the environment.

newswatch's LLM tasks -- summarizing an article, repairing a broken crawl selector --
run on the thinchat library, which speaks to every provider behind one interface.
Keys are read from the provider's standard environment variable. Gemini's free tier
is the default backend for the light summary task."""

from __future__ import annotations

import os

from thinchat import PROVIDERS, Client, make_client
from thinchat.errors import ThinchatError
from thinchat.keys import ENV_BY_PROVIDER

from newswatch.errors import LLMError

__all__ = ["DEFAULT_PROVIDER", "PROVIDERS", "make_llm_client"]

DEFAULT_PROVIDER = "gemini"
_MAX_RETRIES = 6


def make_llm_client(
    provider: str = DEFAULT_PROVIDER, *, model: str | None = None,
    api_key: str | None = None, max_tokens: int, action: str,
) -> Client:
    """Build the thinchat client for ``provider``. The key comes from ``api_key`` when
    given, else the provider's standard env var; ``model`` overrides the default;
    ``max_tokens`` caps the reply; ``action`` names the caller in the missing-key
    message.

    Raises:
        LLMError: unknown provider, no API key available for it, or the client could
            not be constructed.
    """
    if provider not in PROVIDERS:
        raise LLMError(f"unknown LLM provider {provider!r}; choose one of {', '.join(PROVIDERS)}")
    env_name = ENV_BY_PROVIDER.get(provider)
    key = api_key if api_key is not None else (os.environ.get(env_name) if env_name else None)
    if env_name is not None and not key:
        raise LLMError(f"{action} needs an API key for {provider}; set {env_name}")
    try:
        return make_client(provider, model=model, api_key=key,
                           max_tokens=max_tokens, max_retries=_MAX_RETRIES)
    except ThinchatError as err:
        raise LLMError(f"{action} could not start {provider}: {err}") from err
