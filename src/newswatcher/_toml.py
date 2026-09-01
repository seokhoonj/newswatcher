"""The small TOML pieces the ``topics`` and ``sources`` registries both need: encode a
string or a list of strings as a TOML value, and read a ``[[key]]`` table array back.

The read side is the mirror of ``_atomic`` on the write side -- both registries store a
table array of records in ``config_dir()`` and were repeating the same parse-and-validate
boilerplate. Each registry still renders its own record blocks (their fields differ); only
these primitives, which do not, live here. Python's ``tomllib`` reads TOML but cannot write
it, so the encoders are hand-rolled -- a TOML basic string is spelled exactly like a JSON
string, so ``json.dumps`` produces one (with the right escaping) for free.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

__all__ = ["array", "quote", "read_table_array"]


def quote(value: str) -> str:
    """Encode ``value`` as a TOML basic string, quoted and escaped (``na"me`` ->
    ``"na\\"me"``). Non-ASCII is kept verbatim, matching the human-edited files."""
    return json.dumps(value, ensure_ascii=False)


def array(words: tuple[str, ...]) -> str:
    """Encode ``words`` as a TOML inline array of basic strings (``["a", "b"]``)."""
    return "[" + ", ".join(quote(word) for word in words) + "]"


def read_table_array(
    path: Path, key: str, error_cls: type[Exception]
) -> list[dict[str, object]]:
    """Read ``path`` and return the entries of its ``[[key]]`` table array (each a dict);
    empty when the key is absent. Non-dict entries are skipped.

    Raises:
        error_cls: the file is unreadable or not valid TOML, or ``key`` holds something
            other than a table array (a scalar ``key = ...`` instead of ``[[key]]``). The
            caller passes its own domain error type so the message names the right file.
    """
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as err:
        # UnicodeDecodeError is a ValueError, not an OSError, so a non-UTF-8 file must be
        # named explicitly or it escapes this boundary as a bare traceback.
        raise error_cls(f"could not read {path}: {err}") from err
    entries = parsed.get(key)
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise error_cls(f"{path}: [{key}] must be a table array ([[{key}]])")
    return [entry for entry in entries if isinstance(entry, dict)]
