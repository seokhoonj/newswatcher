"""Build a thinchat LLM client, letting thinchat resolve the provider's key.

newswatcher's LLM tasks -- summarizing an article, repairing a broken crawl selector -- run on
the thinchat library, which speaks to every provider behind one interface. The key is thinchat's
to resolve: an explicit ``api_key`` override wins, then the provider's standard environment
variable, then thinchat's own store (``thinchat set <provider>``, which ``newswatcher setup``
drives). newswatcher keeps no key of its own -- summarizing is newswatcher's job, but the LLM
credential belongs with thinchat, the tool that speaks to the provider. Gemini's free tier is the
default backend for the light summary task.

thinchat scrubs any provider key from its own error messages and the exception chain beneath
them, so newswatcher interpolates a ``ThinchatError`` directly without re-redacting it."""

from __future__ import annotations

from thinchat import PROVIDERS, Client, get_api_key, make_client
from thinchat.errors import ThinchatError
from thinchat.keys import ENV_BY_PROVIDER

from newswatcher.errors import LLMError

__all__ = ["DEFAULT_PROVIDER", "PROVIDERS", "make_llm_client", "provider_key_name",
           "validate_provider"]

DEFAULT_PROVIDER = "gemini"
_MAX_RETRIES = 6


def validate_provider(provider: str) -> None:
    """Check that ``provider`` is a backend thinchat knows -- the single home for this check, so
    the CLI's early validation and ``make_llm_client`` give the same message.

    Raises:
        LLMError: the provider is not a known backend.
    """
    if provider not in PROVIDERS:
        raise LLMError(
            f"unknown LLM provider {provider!r}; choose one of {', '.join(sorted(PROVIDERS))}")


def provider_key_name(provider: str) -> str | None:
    """The environment-variable / store name that holds ``provider``'s API key
    (``GEMINI_API_KEY`` ...), or ``None`` for a keyless provider (ollama runs locally and needs
    none). The single home for this mapping, so the CLI's ``set-key`` and ``make_llm_client``
    agree on the name a key is stored under."""
    return ENV_BY_PROVIDER.get(provider)


def make_llm_client(
    provider: str = DEFAULT_PROVIDER, *, model: str | None = None,
    api_key: str | None = None, max_tokens: int, action: str,
) -> Client:
    """Build the thinchat client for ``provider``. The key is resolved by thinchat -- ``api_key``
    when given, else the provider's standard env var, else thinchat's own store; ``model``
    overrides the default; ``max_tokens`` caps the reply; ``action`` names the caller in the
    missing-key message. A keyless provider (ollama) needs no key.

    Raises:
        LLMError: unknown provider, no API key available for a keyed provider, thinchat's store
            was unreadable, or the client could not be constructed.
    """
    validate_provider(provider)
    env_name = provider_key_name(provider)
    if env_name is None:
        key = api_key   # keyless (ollama): honor an explicit key if given, else none
    else:
        # thinchat owns the key (override > env > its own store). Resolve it here only to raise a
        # friendly, action-named error before constructing the client; the store is thinchat's.
        try:
            resolved_secret = get_api_key(provider, override=api_key)
        except ThinchatError as err:
            raise LLMError(f"{action} could not read the stored key for {provider}: {err}") from err
        key = resolved_secret.reveal() if resolved_secret is not None else None
        if not key:
            raise LLMError(
                f"{action} needs an API key for {provider}; set {env_name} "
                f"or run 'newswatcher setup' (it stores the key with thinchat)")
    try:
        return make_client(provider, model=model, api_key=key,
                           max_tokens=max_tokens, max_retries=_MAX_RETRIES)
    except ThinchatError as err:
        raise LLMError(f"{action} could not start {provider}: {err}") from err
