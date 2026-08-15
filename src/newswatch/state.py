"""Between-run state, keyed by source name: the dedup watermark and the empty-poll
counter the healer reads.

- ``seen_guid_by_source`` / ``published_by_source`` -- the newest item already
  collected per source: its guid and its published time. An item is new when its guid
  differs from the stored one AND its published time is not older than the stored one
  (so a re-listed old article is not re-collected, while a genuinely newer article
  is). Losing this re-collects a backlog, so it is written atomically.
- ``empty_polls_by_source`` -- consecutive polls where a crawl source's listing
  fetched fine but its ``item`` selector matched zero rows. The healer triggers at a
  threshold; a poll that finds rows clears it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from newswatch._atomic import write_bytes_atomic
from newswatch.config import state_dir
from newswatch.errors import ConfigError
from newswatch.feed import FeedItem

__all__ = ["State", "read_state", "write_state", "state_path"]

_SEEN_KEY = "seen_guid_by_source"
_PUBLISHED_KEY = "published_by_source"
_EMPTY_KEY = "empty_polls_by_source"


@dataclass
class State:
    """newswatch's between-run state. All three maps are mutable; a poll advances them
    in place and persists once through ``write_state``."""

    seen_guid_by_source:   dict[str, str] = field(default_factory=dict)
    published_by_source:   dict[str, str] = field(default_factory=dict)
    empty_polls_by_source: dict[str, int] = field(default_factory=dict)

    def is_new(self, source_name: str, item: FeedItem) -> bool:
        """Whether ``item`` is newer than the source's watermark. New when its guid is
        unseen and its published time (when both sides have one) is not older than the
        stored newest."""
        if item.guid == self.seen_guid_by_source.get(source_name):
            return False
        newest = self.published_by_source.get(source_name, "")
        if newest and item.published and item.published < newest:
            return False
        return True

    def mark_seen(self, source_name: str, item: FeedItem) -> None:
        """Advance the source's watermark to ``item`` when it is at least as recent as
        the stored newest (or the source has no stored time yet)."""
        newest = self.published_by_source.get(source_name, "")
        if not newest or not item.published or item.published >= newest:
            self.seen_guid_by_source[source_name] = item.guid
            if item.published:
                self.published_by_source[source_name] = item.published

    def note_empty(self, source_name: str) -> int:
        """Increment and return the source's consecutive empty-poll count."""
        count = self.empty_polls_by_source.get(source_name, 0) + 1
        self.empty_polls_by_source[source_name] = count
        return count

    def clear_empty(self, source_name: str) -> None:
        """Reset the source's empty-poll count (a poll found rows)."""
        self.empty_polls_by_source.pop(source_name, None)


def state_path() -> Path:
    """The state ledger, ``state.json`` in ``state_dir()``.

    Raises:
        ConfigError: no state directory can be resolved (propagated from ``state_dir``)."""
    return state_dir() / "state.json"


def read_state(path: Path | None = None) -> State:
    """Return the persisted ``State``; an empty one when there is no file or it is
    corrupt. A genuine I/O error is not swallowed (reading it as empty would let the
    next write wipe real watermarks).

    Raises:
        ConfigError: the state file exists but could not be read (an I/O error).
    """
    path = path or state_path()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return State()
    except (OSError, UnicodeDecodeError) as err:
        raise ConfigError(f"could not read state file {path}: {err}") from err
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return State()
    if not isinstance(parsed, dict):
        return State()
    return State(
        seen_guid_by_source=_str_pairs(parsed.get(_SEEN_KEY)),
        published_by_source=_str_pairs(parsed.get(_PUBLISHED_KEY)),
        empty_polls_by_source=_int_pairs(parsed.get(_EMPTY_KEY)),
    )


def write_state(state: State, path: Path | None = None) -> None:
    """Persist ``state`` atomically, keys sorted so the file diffs cleanly.

    Raises:
        ConfigError: the state file could not be written (an I/O error).
    """
    path = path or state_path()
    payload = {
        _SEEN_KEY: _sorted(state.seen_guid_by_source),
        _PUBLISHED_KEY: _sorted(state.published_by_source),
        _EMPTY_KEY: _sorted(state.empty_polls_by_source),
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    write_bytes_atomic(path, data, ConfigError)


def _str_pairs(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}


def _int_pairs(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items()
            if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)}


def _sorted(mapping: Mapping[str, object]) -> dict[str, object]:
    return {key: mapping[key] for key in sorted(mapping)}
