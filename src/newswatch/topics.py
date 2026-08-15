"""The set of topics the user watches, read from ``topics.toml`` in ``config_dir()``.

A topic is a named keyword filter. ``includes`` keeps an article whose title or
summary contains any listed word (whole-word, case-insensitive); an empty
``includes`` matches every article. ``excludes`` then drops an article mentioning
any listed word. A source subscribes to topics by name (see ``sources``); this
module only reads and writes the topic definitions.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from newswatch._atomic import write_text_atomic
from newswatch.config import config_dir
from newswatch.errors import TopicError

__all__ = ["Topic", "topics_path", "load_topics", "add_topic"]


@dataclass(frozen=True, slots=True)
class Topic:
    """One topic: a name and its keyword filter. ``includes`` keeps an article
    matching any listed word (empty = keep all); ``excludes`` then drops any article
    matching a listed word. Words are matched whole-word, case-insensitive, over the
    article title + summary (the test lives in ``match``)."""

    name: str
    includes: tuple[str, ...] = field(default=(), kw_only=True)
    excludes: tuple[str, ...] = field(default=(), kw_only=True)


def topics_path() -> Path:
    """The topics file, ``topics.toml`` in ``config_dir()``.

    Raises:
        ConfigError: no config directory can be resolved (propagated from ``config_dir``).
    """
    return config_dir() / "topics.toml"


def load_topics(path: Path | None = None) -> tuple[Topic, ...]:
    """Read the topics list from ``path`` (default ``topics_path()``); empty tuple
    when the file is absent.

    Raises:
        TopicError: the file is unreadable or an entry is missing ``name``.
    """
    path = path or topics_path()
    if not path.exists():
        return ()
    return tuple(_topic_from(entry, path) for entry in _read_entries(path))


def add_topic(topic: Topic, path: Path | None = None) -> bool:
    """Append ``topic`` to ``topics.toml``, creating the file if absent; return
    whether it was added (False if the name already exists — a no-op, so ``add-topic``
    is idempotent). The file is rewritten from the parsed-and-appended list so a
    hand-edited file is normalised and a duplicate cannot slip in.

    Raises:
        TopicError: the existing file is malformed or could not be written.
    """
    path = path or topics_path()
    existing = load_topics(path) if path.exists() else ()
    if any(current.name == topic.name for current in existing):
        return False
    write_text_atomic(path, _render((*existing, topic)), TopicError)
    return True


def _read_entries(path: Path) -> list[dict[str, object]]:
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as err:
        raise TopicError(f"could not read {path}: {err}") from err
    entries = parsed.get("topic")
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise TopicError(f"{path}: [topic] must be a table array ([[topic]])")
    return [entry for entry in entries if isinstance(entry, dict)]


def _topic_from(entry: dict[str, object], path: Path) -> Topic:
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise TopicError(f"a [[topic]] in {path} is missing 'name'")
    return Topic(
        name.strip(),
        includes=_keywords(entry.get("includes", ()), "includes", name),
        excludes=_keywords(entry.get("excludes", ()), "excludes", name),
    )


def _keywords(raw: object, field_name: str, name: object) -> tuple[str, ...]:
    if isinstance(raw, str):
        raw = [raw]
    elif not isinstance(raw, (list, tuple)):
        raise TopicError(
            f"topic {name!r}: {field_name} must be a string or a list, got {type(raw).__name__}"
        )
    return tuple(str(word) for word in raw)


def _render(topics: tuple[Topic, ...]) -> str:
    blocks = []
    for topic in topics:
        lines = ["[[topic]]", f"name = {_toml_str(topic.name)}"]
        if topic.includes:
            lines.append(f"includes = {_toml_list(topic.includes)}")
        if topic.excludes:
            lines.append(f"excludes = {_toml_list(topic.excludes)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def _toml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_list(words: tuple[str, ...]) -> str:
    return "[" + ", ".join(_toml_str(word) for word in words) + "]"
