"""Orchestrate the component tools' credential stores for ``setup`` and ``doctor``.

newswatcher owns no secrets. The LLM key lives with thinchat, the email password with mailmail,
the chat token with pushpush -- each in its own store, exactly as if the tool were used
standalone. This module is the one place that knows which channels newswatcher drives and how to
inspect, set, and locate each tool's secret, so ``newswatcher setup`` and ``newswatcher doctor``
speak one vocabulary. It stores nothing of its own.

A channel is a ``(config entity, secret)`` pair: an LLM provider whose key is thinchat's, a
mailmail account whose SMTP password is mailmail's, a pushpush route whose token is pushpush's.
``setup`` fills the missing secrets for entities that already exist in each tool's config; it never
creates the accounts or routes themselves (that is each tool's own config UX). ``doctor`` reports
the map, and never prints a secret.
"""

from __future__ import annotations

import enum
import functools
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import credbox
import thinchat

# mailmail and pushpush are optional extras (newswatcher[email] / newswatcher[chat]), so they are
# imported lazily inside the channel builders -- importing this module (and the CLI that reads it)
# must not require a delivery package the user did not install.
from newswatcher._llm import provider_key_name, validate_provider
from newswatcher.errors import ConfigError

__all__ = ["Channel", "ChannelState", "channels", "display_path", "legacy_llm_store"]


class ChannelState(enum.Enum):
    """Where a channel's secret stands. ``SET`` -- it resolves (an env var or the tool's store);
    ``MISSING`` -- the config entity exists but no secret does, so ``setup`` can fill it;
    ``UNCONFIGURED`` -- the tool has no such entity yet, so it is configured with the tool first;
    ``NOT_INSTALLED`` -- the channel's optional package is not installed (delivery is opt-in);
    ``ERROR`` -- the tool's store could not be read (a content-free message, never the secret)."""

    SET = "set"
    MISSING = "missing"
    UNCONFIGURED = "unconfigured"
    NOT_INSTALLED = "not_installed"
    ERROR = "error"


@dataclass(frozen=True)
class Channel:
    """One ``(config entity, secret)`` newswatcher drives, and how to inspect and fill it.

    ``label`` names it for a human (``LLM key (gemini)``, ``email me@host``, ``chat alerts``);
    ``tool`` is the owning package; ``location`` is that tool's store path (for display only);
    ``state`` is the secret's standing; ``detail`` carries the hint when ``UNCONFIGURED`` or the
    error text when ``ERROR`` (``None`` otherwise); ``setter`` stores a value in the owning tool's
    store and is present only when ``state is ChannelState.MISSING``.
    """

    label: str
    tool: str
    location: str
    state: ChannelState
    detail: str | None = None
    setter: Callable[[str], None] | None = None

    def __post_init__(self) -> None:
        # A setter is present exactly when the secret is fillable (MISSING), so a caller can treat
        # "MISSING" and "setter is not None" as one fact. Enforced here, not merely asserted at the
        # call site, so it holds even under `python -O` (which strips asserts).
        if (self.setter is not None) != (self.state is ChannelState.MISSING):
            raise ValueError(
                f"a setter must be present iff state is MISSING; got state={self.state} "
                f"with setter={'set' if self.setter else 'None'}")


def channels(llm_provider: str) -> list[Channel]:
    """Every channel newswatcher drives -- the ``llm_provider``'s key, then each configured mailmail
    account and pushpush route -- with each secret's current standing. The single source both
    ``setup`` and ``doctor`` render; the CLI resolves ``llm_provider`` since it owns that setting.

    Raises:
        LLMError: ``llm_provider`` is not a backend thinchat knows (a typo in the configured
            default), surfaced before any store is touched.
    """
    return [_llm_channel(llm_provider), *_email_channels(), *_chat_channels()]


def legacy_llm_store() -> str | None:
    """Where the pre-0.1 newswatcher LLM store lives when it still holds keys, else ``None``.

    Before newswatcher handed the LLM key to thinchat it kept its own store; ``setup`` points a user
    whose legacy store is populated at the one-time ``credbox migrate`` that moves the keys to
    thinchat (the key names already match). The location comes from credbox's own secret-free
    description of newswatcher's historical binding (not a recomputed path, so an encrypted/keyring
    legacy store reads right too), home collapsed to ``~``. An unreadable or absent store reads as
    ``None``.
    """
    try:
        store = credbox.Credentials("newswatcher")
        if store.names():
            return _collapse_home(store.store_location())
    except credbox.CredBoxError:
        return None
    return None


def _llm_channel(provider: str) -> Channel:
    """The LLM channel for ``provider``: whether thinchat can find its key, and how to store one.
    A keyless provider (ollama runs locally) is always ``SET``."""
    validate_provider(provider)   # a typo in the configured default is an error, not a silent skip
    location = _store_location("thinchat")
    if provider_key_name(provider) is None:
        return Channel(f"LLM ({provider}, keyless)", "thinchat", location, ChannelState.SET)
    label = f"LLM key ({provider})"
    try:
        available = thinchat.get_api_key(provider) is not None
    except thinchat.ThinchatError:
        # Content-free, like the email/chat read paths: this line reaches the terminal, and the
        # tool's message is not newswatcher's to vouch for. The user runs thinchat for specifics.
        return Channel(label, "thinchat", location, ChannelState.ERROR,
                       detail="the stored key could not be read")
    if available:
        return Channel(label, "thinchat", location, ChannelState.SET)
    return Channel(label, "thinchat", location, ChannelState.MISSING,
                   setter=_make_setter(functools.partial(_put_llm_key, provider),
                                       label, thinchat.ThinchatError))


def _email_channels() -> list[Channel]:
    """One channel per configured mailmail sender account: whether its SMTP password resolves, and
    how to store one. No account configured -> a single ``UNCONFIGURED`` channel; mailmail not
    installed (the optional ``newswatcher[email]`` extra) -> a single ``NOT_INSTALLED`` channel."""
    try:
        import mailmail
    except ImportError:
        return [Channel("email", "mailmail", "-", ChannelState.NOT_INSTALLED,
                        detail="add it with 'pip install newswatcher[email]'")]
    location = _store_location("mailmail")
    try:
        mail_config = mailmail.load_config()
    except mailmail.ConfigError as err:
        if _is_missing_config(err):
            return [Channel("email", "mailmail", location, ChannelState.UNCONFIGURED,
                            detail="configure a sender account with mailmail first")]
        return [Channel("email", "mailmail", location, ChannelState.ERROR,
                        detail="the mailmail config could not be read")]
    result: list[Channel] = []
    for account in mail_config.account_by_handle.values():
        label = f"email {account.email}"
        try:
            mailmail.resolve_password(account)
        except mailmail.MissingPasswordError:
            result.append(Channel(label, "mailmail", location, ChannelState.MISSING,
                                  setter=_make_setter(functools.partial(mailmail.store_password, account),
                                                      label, mailmail.MailmailError)))
        except mailmail.MailmailError:
            # Any other read failure (unreadable store, keyring-backend error, a bad binding):
            # report it as ERROR with a content-free detail. The message is NOT the tool's error
            # text -- an unaudited sibling makes no scrub guarantee, and this line reaches the
            # terminal. Catching the package base (not just CredentialsError) keeps doctor, a
            # diagnostic that must never crash, from dying on a foreign store-read exception.
            result.append(Channel(label, "mailmail", location, ChannelState.ERROR,
                                  detail="the stored password could not be read"))
        else:
            result.append(Channel(label, "mailmail", location, ChannelState.SET))
    return result


def _chat_channels() -> list[Channel]:
    """One channel per configured pushpush route: whether its token resolves, and how to store one.
    No route configured -> a single ``UNCONFIGURED`` channel; pushpush not installed (the optional
    ``newswatcher[chat]`` extra) -> a single ``NOT_INSTALLED`` channel."""
    try:
        import pushpush
    except ImportError:
        return [Channel("chat", "pushpush", "-", ChannelState.NOT_INSTALLED,
                        detail="add it with 'pip install newswatcher[chat]'")]
    location = _store_location("pushpush")
    try:
        push_config = pushpush.load_config()
    except pushpush.ConfigError as err:
        if _is_missing_config(err):
            return [Channel("chat", "pushpush", location, ChannelState.UNCONFIGURED,
                            detail="configure a chat route with pushpush first")]
        return [Channel("chat", "pushpush", location, ChannelState.ERROR,
                        detail="the pushpush config could not be read")]
    result: list[Channel] = []
    for route in push_config.route_by_name.values():
        label = f"chat {route.name}"
        try:
            pushpush.resolve_secret(route)
        except pushpush.MissingSecretError:
            result.append(Channel(label, "pushpush", location, ChannelState.MISSING,
                                  setter=_make_setter(functools.partial(pushpush.store_secret, route),
                                                      label, pushpush.PushpushError)))
        except pushpush.PushpushError:
            # As in _email_channels: any other read failure is a content-free ERROR (never the
            # tool's own message), and catching the package base keeps doctor from crashing on a
            # foreign store-read exception.
            result.append(Channel(label, "pushpush", location, ChannelState.ERROR,
                                  detail="the stored token could not be read"))
        else:
            result.append(Channel(label, "pushpush", location, ChannelState.SET))
    return result


def _put_llm_key(provider: str, value: str) -> None:
    """Store ``value`` as ``provider``'s key with thinchat. A positional-value wrapper so
    ``functools.partial(_put_llm_key, provider)`` yields a ``Callable[[str], None]`` -- thinchat's
    own ``set_api_key`` takes ``value`` keyword-only, which a bare partial cannot fill positionally."""
    thinchat.set_api_key(provider, value=value)


def _make_setter(store: Callable[[str], None], label: str,
                 tool_error: type[Exception]) -> Callable[[str], None]:
    """Build a setter that wraps a tool's store call so a failure surfaces as newswatcher's own
    ``ConfigError`` rather than the tool's foreign type -- keeping ``setup``'s catch surface
    newswatcher-only, so one channel's failure can be reported and the next still tried.

    Unlike the read paths (whose ERROR detail is content-free), this write-path error keeps the
    tool's message: a *store* failure is a blank-value refusal or a filesystem/backend error --
    about the write, never quoting the value -- and the value here is the one the user just typed,
    so it is theirs to see, not a disclosure."""

    def run(value: str) -> None:
        try:
            store(value)
        except tool_error as err:
            raise ConfigError(f"could not store {label}: {err}") from err

    return run


def _is_missing_config(err: Exception) -> bool:
    """Whether a tool's ``ConfigError`` means "not configured yet" (an absent file, or a valid file
    that defines no accounts/routes) rather than "corrupt". Both mailmail and pushpush chain a
    ``FileNotFoundError`` cause only when the file is absent, and raise without a cause when the file
    parses but is empty; a real corruption (bad TOML/UTF-8, a read error) chains that cause. So a
    corrupt config surfaces as ``ERROR`` (which ``doctor`` counts) instead of a misleading
    ``UNCONFIGURED`` that would let a scheduled run's gate pass over a broken setup."""
    cause = err.__cause__
    return cause is None or isinstance(cause, FileNotFoundError)


def _store_location(app: str) -> str:
    """Where ``app``'s secrets actually live, as credbox's own secret-free description -- the real
    backend's file path or keyring service, honoring the resolved binding, rather than assuming a
    plaintext ``credentials.json`` (which would misreport an encrypted or keyring store). Home is
    collapsed to ``~``; a best-effort default if the binding cannot be resolved (the string is shown
    to the user, never read here)."""
    try:
        return _collapse_home(credbox.Credentials.for_app(app).store_location())
    except credbox.CredBoxError:
        return f"~/.config/{app}/credentials.json"


def _collapse_home(location: str) -> str:
    """``location`` with a leading home directory shown as ``~`` for a compact display. A no-op when
    it is not a home path (a keyring-service description, an absolute path elsewhere)."""
    home = str(Path.home())
    return location.replace(home, "~", 1) if location.startswith(home) else location


def display_path(path: Path) -> str:
    """``path`` with the home directory collapsed to ``~`` for a compact display, or unchanged when
    it is not under home. Shared with the CLI so a store path and a config path read alike."""
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)
