"""newswatch's non-secret settings, and the base directories for everything it
writes on the machine.

Settings are not secrets, so they live in a plain, hand-editable TOML file,
``config.toml`` in ``config_dir()``.

Files are placed by *kind*, not all in one directory. Each kind has its own base
directory, resolved here from the XDG base-directory env vars (falling back to
``~/.config``, ``~/.local/share``, ``~/.local/state``) -- the *same* layout on
every OS, no platform library. macOS and Windows get the XDG locations too, which
is the convention git / ssh / aws already use there, and keeps the package light:

- ``config_dir()`` -- hand-editable ``config.toml``, ``topics.toml``, and
  ``sources.toml``.
- ``data_dir()`` -- durable, hard-to-regenerate user data: the article archive.
- ``state_dir()`` -- run state that persists but is neither hand-edited nor
  precious: watermarks and the scheduler's log.

Every consumer module hangs its own file off one of these bases rather than
re-deriving a path.

A setting is read from the environment first (``NEWSWATCH_DIGEST_TO`` ...), then
the file, so a one-off environment value overrides it without editing anything.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from newswatch.errors import ConfigError

_APP = "newswatch"

__all__ = [
    "config_dir",
    "config_path",
    "data_dir",
    "state_dir",
    "load_settings",
    "setting",
]


def config_dir() -> Path:
    """Hand-editable settings: ``config.toml``, ``topics.toml``, ``sources.toml``.

    ``$XDG_CONFIG_HOME/newswatch`` when that variable is set, else
    ``~/.config/newswatch`` -- the same on every OS (the git / ssh / aws
    convention), not a platform-native dir. git never tracks it.

    Raises:
        ConfigError: no home directory can be determined and no absolute
            ``XDG_CONFIG_HOME`` is set (propagated from ``_xdg_app_dir``).
    """
    return _xdg_app_dir("XDG_CONFIG_HOME", ".config")


def data_dir() -> Path:
    """Durable, hard-to-regenerate user data: the article archive.

    A ``data_dir`` in ``config.toml`` (or the ``NEWSWATCH_DATA_DIR`` env var) wins,
    taken as an explicit path used as-is (``~`` expanded, no app-name appended) --
    read every run, so a large archive can live on another volume and an interactive
    run and a cron run agree without touching the environment. Otherwise
    ``$XDG_DATA_HOME/newswatch``, else ``~/.local/share/newswatch`` (the same on every
    OS). (``config_dir`` has no such key -- config cannot name its own location.) Kept
    apart from ``config_dir()`` so resetting settings never destroys the archive.

    Raises:
        ConfigError: no home directory can be determined and no absolute
            ``XDG_DATA_HOME`` / override is set (propagated from ``_xdg_app_dir``).
    """
    override = _dir_override("NEWSWATCH_DATA_DIR")
    if override is not None:
        return override
    return _xdg_app_dir("XDG_DATA_HOME", ".local/share")


def state_dir() -> Path:
    """Run state that persists but is neither hand-edited nor precious: watermarks
    and the scheduler's log.

    A ``state_dir`` in ``config.toml`` (or ``NEWSWATCH_STATE_DIR``) wins, as an
    explicit path used as-is (``~`` expanded) -- symmetric with ``data_dir``, so a
    caller who wants to relocate state can, though it is small enough that most do
    not. Otherwise ``$XDG_STATE_HOME/newswatch``, else ``~/.local/state/newswatch``
    (the same on every OS).

    Raises:
        ConfigError: no home directory can be determined and no absolute
            ``XDG_STATE_HOME`` / override is set (propagated from ``_xdg_app_dir``).
    """
    override = _dir_override("NEWSWATCH_STATE_DIR")
    if override is not None:
        return override
    return _xdg_app_dir("XDG_STATE_HOME", ".local/state")


def config_path() -> Path:
    """Where the non-secret settings live: ``config.toml`` in ``config_dir()``.

    Raises:
        ConfigError: propagated from ``config_dir()`` when no config dir can be resolved."""
    return config_dir() / "config.toml"


def load_settings(path: Path | None = None) -> dict[str, object]:
    """Parse ``config.toml`` into a dict; empty when the file is absent.

    Raises:
        ConfigError: the file exists but is not readable TOML -- surfaced as a
            one-line CLI error, not a traceback.
    """
    path = path or config_path()
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as err:
        # tomllib decodes UTF-8 internally, so a non-UTF-8 file raises
        # UnicodeDecodeError (a ValueError, not an OSError) -- name it explicitly
        # or it escapes this boundary as a bare traceback.
        raise ConfigError(f"could not read config file {path}: {err}") from err


def setting(env_name: str) -> str | None:
    """Return a setting from the environment (which wins) or ``config.toml``.

    ``env_name`` is the environment-variable spelling (``NEWSWATCH_DIGEST_TO``); in
    the file it is the same key without the ``NEWSWATCH_`` prefix, lower-cased
    (``digest_to``), since the file already namespaces it (same mapping
    ``_dir_override`` uses). An absent key or an empty string reads as absent
    (``None``) -- the same on both sides, so an empty field falls back to the default
    instead of overriding it. Any other TOML scalar is stringified with ``str()`` (a
    number including ``0``, a bool as ``"True"``/``"False"``): matching the
    environment, where a caller that needs an int parses the returned digits.

    Raises:
        ConfigError: ``config.toml`` exists but is not readable TOML, or no config dir
            can be resolved (propagated from ``load_settings`` / ``config_dir``).
    """
    from_env = os.environ.get(env_name)
    if from_env:
        return from_env
    value = load_settings().get(env_name.removeprefix("NEWSWATCH_").lower())
    return None if value is None or value == "" else str(value)


# --- private resolvers (used by the base-dir functions above) ------------------

def _xdg_app_dir(env_name: str, home_subpath: str) -> Path:
    """newswatch's directory under one XDG base: ``$<env>/newswatch`` when the env
    var holds an absolute path, else ``~/<home_subpath>/newswatch`` (the XDG spec's
    own fallbacks -- ``home_subpath`` is one of ``.config`` / ``.local/share`` /
    ``.local/state``, a home-relative fragment).

    A blank, whitespace-only, *relative*, or unresolvable-``~user`` env value is ignored
    and the home fallback is used: the XDG spec says a relative path "must be ignored"
    (a relative value would put the dir under the current working directory, splitting a
    cron run at cwd ``/`` from an interactive run at cwd ``~``), and a ``~user`` whose
    home cannot be resolved must not crash a resolver an advisory env var drives.
    Applied on every OS -- no platform-dirs library.

    Raises:
        ConfigError: no absolute env value was given and no home directory can be
            determined for the ``~/<home_subpath>`` fallback (HOME unset and the uid
            has no passwd entry) -- converted from the bare ``RuntimeError``
            ``Path.home`` throws, so it stays inside the CLI's error surface."""
    base = os.environ.get(env_name, "").strip()
    root = _as_absolute(base) if base else None
    if root is not None:
        return root / _APP
    try:
        home = Path.home()
    except RuntimeError as err:
        raise ConfigError(
            f"cannot locate ~/{home_subpath}/{_APP}: no home directory "
            f"(set HOME, or set {env_name} to an absolute path)"
        ) from err
    return home / home_subpath / _APP


def _dir_override(env_name: str) -> Path | None:
    """A base-dir override from the environment (which wins) or ``config.toml``, as an
    explicit absolute path with ``~`` expanded, or ``None`` when unset (or not absolute).

    Tolerates an unreadable config file by reading it as absent, rather than raising a
    second time: the CLI validates the config once at entry, and a malformed file
    surfaces there and through ``setting``. A non-string (``data_dir = 12345``), blank,
    or non-absolute value reads as absent too, so it never becomes a path resolved
    against the working directory."""
    from_env = os.environ.get(env_name, "").strip()
    if from_env:
        return _as_absolute(from_env)
    try:
        value = load_settings().get(env_name.removeprefix("NEWSWATCH_").lower())
    except ConfigError:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return _as_absolute(value)


def _as_absolute(raw: str) -> Path | None:
    """Expand ``~`` in ``raw`` and return it only if absolute, else ``None``. Never
    raises: a relative value is ignored (it would depend on the working directory), and
    a ``~user`` whose home cannot be resolved (``expanduser`` raises ``RuntimeError``)
    is treated as absent too -- an advisory env var / config value must not crash the
    resolver."""
    try:
        path = Path(raw).expanduser()
    except RuntimeError:
        return None
    return path if path.is_absolute() else None
