"""Between-run state, keyed by source name: the dedup watermark and the empty-poll
counter the healer reads.

- ``seen_guids_by_source`` -- the recently-collected guids per source, oldest first.
  An item is new exactly when its guid is not in this set, so dedup is by identity
  alone: an item is re-collected only if we have genuinely never seen its guid. The
  set is bounded to ``_SEEN_CAP`` most-recent guids per source (older guids are
  evicted and would re-collect once if a source re-lists them), so it cannot grow
  without bound. Losing this re-collects a backlog, so it is written atomically.
- ``empty_polls_by_source`` -- consecutive polls where a crawl source's listing
  fetched fine but its ``item`` selector matched zero rows. The healer triggers at a
  threshold; a poll that finds rows clears it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from newswatcher._atomic import write_bytes_atomic
from newswatcher.config import state_dir
from newswatcher.errors import ConfigError
from newswatcher.feed import FeedItem

__all__ = ["State", "read_state", "write_state", "state_path"]

_SEEN_KEY = "seen_guids_by_source"
_EMPTY_KEY = "empty_polls_by_source"
_SEEN_CAP = 1024


@dataclass(slots=True)
class State:
    """newswatcher's between-run state. Both maps are mutable; a poll advances them in
    place and persists once through ``write_state``."""

    seen_guids_by_source:  dict[str, list[str]] = field(default_factory=dict)
    empty_polls_by_source: dict[str, int]       = field(default_factory=dict)

    def is_new(self, source_name: str, item: FeedItem) -> bool:
        """Whether ``item``'s guid has not been collected recently for this source."""
        return item.guid not in self.seen_guids_by_source.get(source_name, ())

    def mark_seen(self, source_name: str, item: FeedItem) -> None:
        """Record ``item``'s guid as the most-recently-seen for this source, evicting
        the oldest guids beyond ``_SEEN_CAP``."""
        seen = self.seen_guids_by_source.setdefault(source_name, [])
        if item.guid in seen:
            seen.remove(item.guid)
        seen.append(item.guid)
        if len(seen) > _SEEN_CAP:
            del seen[: len(seen) - _SEEN_CAP]

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
    """Return the persisted ``State``; an empty one only when there is no file yet. A file
    that exists but is unreadable or corrupt raises rather than reading as empty -- because
    the poll writes the returned state back, so silently reading a corrupt file as empty
    would wipe every source's real watermark (mass re-collect, re-summarize, re-send).

    Raises:
        ConfigError: the state file exists but could not be read or parsed.
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
    except json.JSONDecodeError as err:
        raise ConfigError(
            f"state file {path} is corrupt ({err}); move or delete it to start fresh"
        ) from err
    if not isinstance(parsed, dict):
        return State()
    return State(
        seen_guids_by_source=_str_list_pairs(parsed.get(_SEEN_KEY)),
        empty_polls_by_source=_int_pairs(parsed.get(_EMPTY_KEY)),
    )


def write_state(state: State, path: Path | None = None) -> None:
    """Persist ``state`` atomically, keys sorted so the file diffs cleanly.

    Raises:
        ConfigError: the state file could not be written (an I/O error).
    """
    path = path or state_path()
    payload = {
        _SEEN_KEY: _sorted(state.seen_guids_by_source),
        _EMPTY_KEY: _sorted(state.empty_polls_by_source),
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    write_bytes_atomic(path, data, ConfigError)


def _str_list_pairs(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, list):
            out[key] = [guid for guid in value if isinstance(guid, str)]
    return out


def _int_pairs(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items()
            if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)}


def _sorted(mapping: Mapping[str, object]) -> dict[str, object]:
    return {key: mapping[key] for key in sorted(mapping)}
