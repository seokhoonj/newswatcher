"""Where newswatch keeps its provider API keys.

An LLM provider key -- Gemini's, OpenAI's, Claude's -- is the secret that lets a run
call the summariser (and the selector healer). Keys are looked up in a fixed order, so
an explicit value always wins and a set environment variable beats a file on disk:

1. a key passed in code (``make_llm_client(api_key=...)``)
2. the provider's standard environment variable (``GEMINI_API_KEY``, ``OPENAI_API_KEY``,
   ``CLAUDE_API_KEY``)
3. that same name in ``credentials.json`` under ``config_dir()``

JSON, not the TOML the settings use: a flat ``name -> value`` map with no comments or
types is all a secret file needs, and the key is the same name the environment uses, so
one workflow overrides the other and an existing key store in that shape can be copied
in as-is. Kept out of ``config.toml`` -- that file is for non-secret settings. git never
tracks it. The file is optional: its absence just means "no key here", but a file that is
present and unreadable, not JSON, or not a JSON object is an error, because a caller who
wrote one meant it to be used and a silent skip would hide the mistake.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from newswatch.config import config_dir
from newswatch.errors import ConfigError

__all__ = ["credentials_path", "secret"]


def credentials_path() -> Path:
    """Where newswatch looks for a stored key: ``credentials.json`` beside the settings,
    in ``config_dir()``.

    Raises:
        ConfigError: no config directory can be resolved (propagated from ``config_dir``).
    """
    return config_dir() / "credentials.json"


def secret(name: str) -> str | None:
    """Return the secret stored under ``name`` from the environment (which wins) or the
    credentials file, or ``None`` when neither has it -- so a caller can phrase its own
    "no key" error at the point it is needed.

    ``name`` is the provider's standard environment variable, the same spelling used as
    the key in ``credentials.json``. An empty or blank value on either side reads as
    absent, so an empty field falls back rather than overriding.

    Raises:
        ConfigError: the credentials file exists but is unreadable, not JSON, or not a
            JSON object -- surfaced as a one-line CLI error, not a traceback.
    """
    from_env = os.environ.get(name, "").strip()
    if from_env:
        return from_env
    return _secret_from_file(name)


def _secret_from_file(name: str) -> str | None:
    """Read ``name`` from ``credentials.json``, or ``None`` when the file or the key is
    absent (or its value is not a non-empty string)."""
    path = credentials_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as err:
        # UnicodeDecodeError is a ValueError, not an OSError, so a non-UTF-8 file must be
        # named explicitly or it escapes this boundary as a bare traceback.
        raise ConfigError(f"could not read {path}: {err}") from err
    try:
        store = json.loads(text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path} is not valid JSON: {err}") from err
    if not isinstance(store, dict):
        raise ConfigError(f"{path} must contain a JSON object of name to key")
    key = store.get(name)
    return key.strip() if isinstance(key, str) and key.strip() else None
