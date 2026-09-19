"""The TOML I/O the ``topics``, ``sources`` and ``categories`` registries share: read a
``[[table]]`` array back into records, and append or update one entry in place.

The read side uses the standard library's ``tomllib``. The write side goes through
``tomlite``'s ``TOMLEditor``, which rewrites only the lines an edit touches -- so a
hand-edited file's comments, blank lines and aligned ``=`` columns survive an ``add-*`` or a
selector repair, rather than being flattened by a full re-render. Each registry still owns
its own record shape (their fields differ); only these primitives, which do not, live here.
"""

from __future__ import annotations

import tomllib
from collections.abc import Sequence
from pathlib import Path

from tomlite import TOMLEditor, TomliteError, TOMLValue

__all__ = ["TOMLField", "append_entry", "read_table_array", "update_entry"]

# One ``key = value`` field of a ``[[table]]`` block, as the registries hand it to
# ``append_entry`` / ``update_entry``: a name and a TOML scalar or string array.
TOMLField = tuple[str, TOMLValue]


def read_table_array(
    path: Path, table: str, error_cls: type[Exception]
) -> list[dict[str, object]]:
    """Read ``path`` and return the entries of its ``[[table]]`` array (each a dict); empty
    when the table is absent. Non-dict entries are skipped.

    Raises:
        error_cls: the file is unreadable or not valid TOML, or ``table`` holds something
            other than a table array (a scalar ``table = ...`` instead of ``[[table]]``). The
            caller passes its own domain error type so the message names the right file.
    """
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as err:
        # UnicodeDecodeError is a ValueError, not an OSError, so a non-UTF-8 file must be
        # named explicitly or it escapes this boundary as a bare traceback.
        raise error_cls(f"could not read {path}: {err}") from err
    entries = parsed.get(table)
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise error_cls(f"{path}: [{table}] must be a table array ([[{table}]])")
    return [entry for entry in entries if isinstance(entry, dict)]


def append_entry(
    path: Path,
    table: str,
    fields: Sequence[TOMLField],
    error_cls: type[Exception],
) -> None:
    """Append a new ``[[table]]`` block with ``fields`` (in the given order) to ``path``,
    creating the file if absent and leaving every existing block and comment intact.

    Raises:
        error_cls: the file is unreadable, is not valid UTF-8, uses a TOML construct outside
            tomlite's flat grammar (a multi-line string, a dotted header), or could not be
            written.
    """
    try:
        doc = TOMLEditor.load(path)
        doc.append_to_array(table, fields)
        doc.save(path)
    except (TomliteError, OSError) as err:
        raise error_cls(f"could not write {path}: {err}") from err


def update_entry(
    path: Path,
    table: str,
    *,
    match_field: str,
    match_value: str,
    fields: Sequence[TOMLField],
    error_cls: type[Exception],
) -> None:
    """In the ``[[table]]`` block where ``match_field == match_value``, set each of ``fields``
    -- replacing its line if present, inserting it after the matched field otherwise --
    leaving the rest of the file intact.

    The caller is expected to have already checked the block exists. If none matches, that is
    surfaced as an error rather than silently writing the file back unchanged (the match is on
    the stored value, so a stale or whitespace-padded key would otherwise let a repair quietly
    persist nothing). ``fields`` must not include ``match_field`` itself: changing the matched
    field on the first update would make the remaining updates miss the block.

    Raises:
        error_cls: no ``[[table]]`` block has ``match_field == match_value``; or the file is
            unreadable, is not valid UTF-8, uses a TOML construct outside tomlite's flat
            grammar, or could not be written.
    """
    try:
        doc = TOMLEditor.load(path)
        matched = False
        for field, value in fields:
            if doc.update_in_array(
                    table, match_field=match_field, match_value=match_value,
                    field=field, value=value):
                matched = True
        if fields and not matched:
            raise error_cls(
                f"{path}: no [[{table}]] with {match_field} == {match_value!r}")
        doc.save(path)
    except (TomliteError, OSError) as err:
        raise error_cls(f"could not write {path}: {err}") from err
