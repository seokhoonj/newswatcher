"""The channel map that backs ``newswatcher setup`` and ``newswatcher doctor``.

newswatcher owns no secret: these pin that ``channels()`` reports each tool's secret truthfully,
that a fillable channel stores through its owning tool (never a newswatcher store), that a tool's
own failure surfaces as a newswatcher ``ConfigError``, and that a lingering pre-0.1 store is
detected for the one-time migration. The LLM and unconfigured paths run against real tools on the
suite's tmp config dir; the account/route enumeration is driven with a stubbed tool config.
"""

import types

import pytest

from newswatcher import credentials
from newswatcher.credentials import ChannelState
from newswatcher.errors import ConfigError, LLMError


def _no_provider_key(monkeypatch):
    """Ensure no Gemini key leaks in from the developer's real environment; the autouse tmp XDG
    already gives an empty store and no mailmail/pushpush config."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_channels_on_a_fresh_config(monkeypatch):
    _no_provider_key(monkeypatch)
    by_tool = {channel.tool: channel for channel in credentials.channels("gemini")}
    assert by_tool["thinchat"].state is ChannelState.MISSING   # no key yet, but fillable
    assert by_tool["thinchat"].setter is not None
    assert by_tool["mailmail"].state is ChannelState.UNCONFIGURED   # no account to fill for
    assert by_tool["mailmail"].setter is None
    assert by_tool["pushpush"].state is ChannelState.UNCONFIGURED


def test_llm_channel_is_set_after_storing_a_key(monkeypatch):
    import thinchat

    _no_provider_key(monkeypatch)
    thinchat.set_api_key("gemini", value="stored")
    llm = credentials.channels("gemini")[0]
    assert llm.state is ChannelState.SET
    assert llm.setter is None


def test_keyless_provider_channel_is_set(monkeypatch):
    _no_provider_key(monkeypatch)
    llm = credentials.channels("ollama")[0]
    assert llm.state is ChannelState.SET
    assert "keyless" in llm.label


def test_llm_setter_stores_through_thinchat(monkeypatch):
    import thinchat

    _no_provider_key(monkeypatch)
    llm = credentials.channels("gemini")[0]
    assert llm.state is ChannelState.MISSING
    assert llm.setter is not None
    llm.setter("via-setter")
    resolved = thinchat.get_api_key("gemini")
    assert resolved is not None and resolved.reveal() == "via-setter"


def test_unknown_provider_raises_before_touching_a_store(monkeypatch):
    _no_provider_key(monkeypatch)
    with pytest.raises(LLMError):
        credentials.channels("nope")


def test_llm_channel_reports_error_without_leaking_the_store_message(monkeypatch):
    import thinchat
    from thinchat.errors import ThinchatError

    _no_provider_key(monkeypatch)
    secret_ish = "the-key-AIza-xxxx"

    def boom(provider, **kwargs):
        raise ThinchatError(f"could not read {secret_ish!r}")

    monkeypatch.setattr(thinchat, "get_api_key", boom)
    llm = credentials.channels("gemini")[0]
    assert llm.state is ChannelState.ERROR
    assert llm.setter is None
    assert secret_ish not in (llm.detail or "")   # the tool's message is never rendered


def test_legacy_llm_store_detects_a_populated_newswatcher_store(monkeypatch):
    import credbox

    _no_provider_key(monkeypatch)
    assert credentials.legacy_llm_store() is None   # nothing stored under newswatcher yet
    credbox.Credentials("newswatcher").set("GEMINI_API_KEY", value="old-key")
    location = credentials.legacy_llm_store()
    assert location is not None and "newswatcher" in location


class _Account:
    """A stand-in for mailmail's ``SmtpAccount`` -- the two attributes the map reads."""

    def __init__(self, handle: str, email: str) -> None:
        self.handle = handle
        self.email = email


def _stub_one_mailmail_account(monkeypatch, *, password_stored: dict[str, str]):
    """Point mailmail at a single configured account whose password lives in ``password_stored``."""
    import mailmail

    account = _Account("me", "me@host")

    def resolve(a):
        if "me" in password_stored:
            return password_stored["me"]
        raise mailmail.MissingPasswordError("no password stored")

    monkeypatch.setattr(mailmail, "load_config",
                        lambda: types.SimpleNamespace(account_by_handle={"me": account}))
    monkeypatch.setattr(mailmail, "resolve_password", resolve)


def test_email_channel_enumerates_accounts_and_fills_a_missing_password(monkeypatch):
    import mailmail

    stored: dict[str, str] = {}
    _stub_one_mailmail_account(monkeypatch, password_stored=stored)
    monkeypatch.setattr(mailmail, "store_password",
                        lambda a, pw: stored.__setitem__("me", pw))

    # provider="ollama" keeps the LLM channel keyless so this exercises only the email path.
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.state is ChannelState.MISSING
    assert email.label == "email me@host"
    assert email.setter is not None
    email.setter("smtp-pw")
    assert stored["me"] == "smtp-pw"


def test_email_setter_translates_a_tool_error_to_configerror(monkeypatch):
    import mailmail

    _stub_one_mailmail_account(monkeypatch, password_stored={})

    def boom(account, password):
        raise mailmail.MailmailError("the smtp store is broken")

    monkeypatch.setattr(mailmail, "store_password", boom)
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.setter is not None
    with pytest.raises(ConfigError, match="could not store"):
        email.setter("smtp-pw")


def test_email_channel_is_set_when_the_password_resolves(monkeypatch):
    _stub_one_mailmail_account(monkeypatch, password_stored={"me": "already-there"})
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.state is ChannelState.SET
    assert email.setter is None


def test_email_channel_reports_error_without_leaking_the_store_message(monkeypatch):
    import mailmail

    account = _Account("me", "me@host")
    secret_ish = "p@ss w0rd\x01with-a-control-byte"

    def resolve(a):
        # An unaudited sibling might put the offending value in its error; newswatcher must not
        # render that text. This message deliberately contains the "secret" to prove it is dropped.
        raise mailmail.CredentialsError(f"could not read {secret_ish!r}")

    monkeypatch.setattr(mailmail, "load_config",
                        lambda: types.SimpleNamespace(account_by_handle={"me": account}))
    monkeypatch.setattr(mailmail, "resolve_password", resolve)
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.state is ChannelState.ERROR
    assert email.setter is None
    assert secret_ish not in (email.detail or "")   # the tool's message is never rendered


def test_email_unconfigured_when_the_config_is_absent(monkeypatch):
    import mailmail

    def absent():
        raise mailmail.ConfigError("no configuration file") from FileNotFoundError()

    monkeypatch.setattr(mailmail, "load_config", absent)
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.state is ChannelState.UNCONFIGURED   # nothing configured yet -> not counted


def test_email_reports_error_when_the_config_is_corrupt(monkeypatch):
    import mailmail

    def corrupt():
        # A parse failure chains a non-FileNotFoundError cause; this must be ERROR (which doctor
        # counts), not the "no account" UNCONFIGURED that would let a scheduled gate pass.
        raise mailmail.ConfigError("not valid TOML") from ValueError("bad toml at line 3")

    monkeypatch.setattr(mailmail, "load_config", corrupt)
    email = next(c for c in credentials.channels("ollama") if c.tool == "mailmail")
    assert email.state is ChannelState.ERROR
    assert email.setter is None


def test_chat_reports_error_when_the_config_is_corrupt(monkeypatch):
    import pushpush

    def corrupt():
        raise pushpush.ConfigError("not valid TOML") from ValueError("bad toml")

    monkeypatch.setattr(pushpush, "load_config", corrupt)
    chat = next(c for c in credentials.channels("ollama") if c.tool == "pushpush")
    assert chat.state is ChannelState.ERROR
    assert chat.setter is None


class _Route:
    """A stand-in for pushpush's ``Route`` -- the one attribute the map reads."""

    def __init__(self, name: str) -> None:
        self.name = name


def _stub_one_pushpush_route(monkeypatch, *, secret_stored: dict[str, str]):
    """Point pushpush at a single configured route whose token lives in ``secret_stored``."""
    import pushpush

    route = _Route("alerts")

    def resolve(r):
        if "alerts" in secret_stored:
            return secret_stored["alerts"]
        raise pushpush.MissingSecretError("no secret stored")

    monkeypatch.setattr(pushpush, "load_config",
                        lambda: types.SimpleNamespace(route_by_name={"alerts": route}))
    monkeypatch.setattr(pushpush, "resolve_secret", resolve)


def test_chat_channel_is_set_when_the_token_resolves(monkeypatch):
    _stub_one_pushpush_route(monkeypatch, secret_stored={"alerts": "bot-token"})
    chat = next(c for c in credentials.channels("ollama") if c.tool == "pushpush")
    assert chat.state is ChannelState.SET
    assert chat.label == "chat alerts"
    assert chat.setter is None


def test_chat_channel_fills_a_missing_token(monkeypatch):
    import pushpush

    stored: dict[str, str] = {}
    _stub_one_pushpush_route(monkeypatch, secret_stored=stored)
    monkeypatch.setattr(pushpush, "store_secret",
                        lambda r, secret: stored.__setitem__("alerts", secret))
    chat = next(c for c in credentials.channels("ollama") if c.tool == "pushpush")
    assert chat.state is ChannelState.MISSING
    assert chat.setter is not None
    chat.setter("bot-token")
    assert stored["alerts"] == "bot-token"


def test_chat_channel_reports_error_without_leaking_the_store_message(monkeypatch):
    import pushpush

    route = _Route("alerts")
    secret_ish = "xoxb-secret\x01token"

    def resolve(r):
        raise pushpush.CredentialsError(f"could not read {secret_ish!r}")

    monkeypatch.setattr(pushpush, "load_config",
                        lambda: types.SimpleNamespace(route_by_name={"alerts": route}))
    monkeypatch.setattr(pushpush, "resolve_secret", resolve)
    chat = next(c for c in credentials.channels("ollama") if c.tool == "pushpush")
    assert chat.state is ChannelState.ERROR
    assert chat.setter is None
    assert secret_ish not in (chat.detail or "")


def test_chat_setter_translates_a_tool_error_to_configerror(monkeypatch):
    import pushpush

    _stub_one_pushpush_route(monkeypatch, secret_stored={})

    def boom(route, secret):
        raise pushpush.PushpushError("the chat store is broken")

    monkeypatch.setattr(pushpush, "store_secret", boom)
    chat = next(c for c in credentials.channels("ollama") if c.tool == "pushpush")
    assert chat.setter is not None
    with pytest.raises(ConfigError, match="could not store"):
        chat.setter("bot-token")
