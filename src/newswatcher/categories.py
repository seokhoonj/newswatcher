"""The categories an article can be classified into, read from ``categories.toml`` in
``config_dir()``.

A category is a display label the LLM assigns to an article at summary time: a ``name``
and an optional ``hint`` that guides the model's choice. Unlike a topic (a keyword filter
that decides what is *kept*), a category is a single classification of a kept article --
the summarizer picks the best-fitting one, or none. This module only reads and writes the
category definitions; the choosing lives in ``summarize``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from newswatcher import _toml
from newswatcher.config import config_dir
from newswatcher.errors import CategoryError

__all__ = ["Category", "categories_path", "load_categories", "add_category"]


@dataclass(frozen=True, slots=True)
class Category:
    """One classification label: a ``name`` and an optional ``hint`` describing what
    belongs in it. The hint is persisted in ``categories.toml`` and shown to the LLM to
    guide its choice; only the chosen category *name* is stored on the article, not the
    hint."""

    name: str
    hint: str = field(default="", kw_only=True)


def categories_path() -> Path:
    """The categories file, ``categories.toml`` in ``config_dir()``.

    Raises:
        ConfigError: no config directory can be resolved (propagated from ``config_dir``).
    """
    return config_dir() / "categories.toml"


def load_categories(path: Path | None = None) -> tuple[Category, ...]:
    """Read the categories list from ``path`` (default ``categories_path()``); empty
    tuple when the file is absent (classification is then off).

    Raises:
        CategoryError: the file is unreadable or malformed (invalid TOML, or ``category`` is
            not a ``[[category]]`` table array), an entry is missing ``name``, a ``hint`` is
            not a string, or two names collide when matched case-insensitively (the
            classifier matches names case-insensitively, so such a pair is ambiguous).
    """
    path = path or categories_path()
    if not path.exists():
        return ()
    categories = tuple(_category_from(entry, path)
                       for entry in _toml.read_table_array(path, "category", CategoryError))
    _reject_normalized_collisions(categories, path)
    return categories


def add_category(category: Category, path: Path | None = None) -> bool:
    """Append ``category`` to ``categories.toml``, creating the file if absent; return
    whether it was added (False if a name matching it case-insensitively already exists --
    a no-op, so ``add-category`` is idempotent). The name is stored stripped, and the
    match uses the same case-insensitive normalisation ``load_categories`` enforces, so
    ``add-category`` can never write a file its own reader would then reject.

    Raises:
        CategoryError: the name is empty (or only whitespace), or the existing file is
            malformed or could not be written.
    """
    path = path or categories_path()
    existing = load_categories(path) if path.exists() else ()
    category = Category(category.name.strip(), hint=category.hint.strip())
    if not category.name:
        raise CategoryError("a category name must not be empty")
    normalized = category.name.lower()
    if any(current.name.lower() == normalized for current in existing):
        return False
    _toml.append_entry(path, "category", _fields(category), CategoryError)
    return True


def _reject_normalized_collisions(categories: tuple[Category, ...], path: Path) -> None:
    """Reject two category names that differ only in case or surrounding whitespace: the
    classifier matches a reply's category line case-insensitively, so a colliding pair
    would make one of the two unreachable."""
    category_name_by_normalized: dict[str, str] = {}
    for category in categories:
        normalized_name = category.name.strip().lower()
        if normalized_name in category_name_by_normalized:
            raise CategoryError(
                f"categories {category_name_by_normalized[normalized_name]!r} and "
                f"{category.name!r} in {path} collide when matched case-insensitively; "
                f"give them distinct names")
        category_name_by_normalized[normalized_name] = category.name


def _category_from(entry: dict[str, object], path: Path) -> Category:
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        raise CategoryError(f"a [[category]] in {path} is missing 'name'")
    hint = entry.get("hint", "")
    if not isinstance(hint, str):
        raise CategoryError(
            f"category {name!r}: hint must be a string, got {type(hint).__name__}"
        )
    return Category(name.strip(), hint=hint.strip())


def _fields(category: Category) -> list[_toml.TOMLField]:
    """The ``[[category]]`` fields to write: ``name``, then ``hint`` only when non-empty."""
    fields: list[_toml.TOMLField] = [("name", category.name)]
    if category.hint:
        fields.append(("hint", category.hint))
    return fields
