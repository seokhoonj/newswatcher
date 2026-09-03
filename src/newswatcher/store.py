"""Persist and reload archived articles -- metadata plus our LLM summary. The article
body is never stored: the archive keeps what is ours to keep (title, link, source,
date, matched topics, our summary), not the publisher's text.

One JSON file per article under ``archive_root()``, keyed by a filesystem-safe hash
of the article guid, written atomically. Saving is idempotent -- re-saving the same
guid overwrites in place -- so a re-collected page does not duplicate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from newswatcher._atomic import write_bytes_atomic
from newswatcher.config import data_dir
from newswatcher.errors import ArchiveError
from newswatcher.region import REGIONS, infer_region

__all__ = ["Article", "FileStore", "archive_root"]

_SCHEMA_VERSION = 2   # v2 adds Article.region; v1 files are read with the region inferred
_ARTICLES_DIRNAME = "articles"
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True, slots=True, kw_only=True)
class Article:
    """One archived article: metadata and our summary. No body -- bodies are transient
    summary input, never stored. ``published`` is ISO-8601 (or "") and orders the
    archive; ``topics`` are the names it was tagged with; ``region`` is ``kr``/``intl`` for
    the digest's domestic/overseas split; ``summary`` is our original text and
    ``summary_model`` which model wrote it."""

    guid:          str
    title:         str
    link:          str
    source_name:   str
    published:     str
    topics:        tuple[str, ...]
    summary:       str
    region:        str = field(default="")
    summary_model: str = field(default="")


def archive_root() -> Path:
    """The archive directory, ``archive`` under ``data_dir()``.

    Raises:
        ConfigError: no data directory can be resolved (propagated from ``data_dir``)."""
    return data_dir() / "archive"


class FileStore:
    """A directory of one JSON file per article under ``root`` (default
    ``archive_root()``)."""

    def __init__(self, root: Path | None = None) -> None:
        root = root if root is not None else archive_root()
        self._dir = root / _ARTICLES_DIRNAME

    def save(self, article: Article) -> None:
        """Store ``article`` keyed by its guid; a re-save overwrites in place.

        Raises:
            ArchiveError: the article could not be written (an I/O failure).
        """
        path = self._dir / f"{_key(article.guid)}.json"
        envelope = {
            "schema_version": _SCHEMA_VERSION,
            "saved_at": datetime.now(UTC).strftime(_TIMESTAMP_FORMAT),
            "article": asdict(article),
        }
        payload = json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")
        write_bytes_atomic(path, payload, ArchiveError)

    def load(self, *, topic: str | None = None, since: str | None = None,
             until: str | None = None) -> tuple[Article, ...]:
        """Return archived articles oldest-first, optionally narrowed to a ``topic``
        tag and a half-open date range ``[since, until)`` compared against ``published``
        as ISO-8601 strings (an article with no ``published`` date is ranged and ordered
        by its archive timestamp instead; a bare ``YYYY-MM-DD`` bound works by prefix). A
        corrupt or forward-schema file reads as absent, so one bad file does not sink the
        read.

        Raises:
            ArchiveError: a stored file could not be read (an I/O failure, as opposed to
                a corrupt or forward-schema file, which is skipped).
        """
        rows: list[tuple[str, Article]] = []
        for path in self._dir.glob("*.json"):
            article, saved_at = _read_article(path)
            if article is None:
                continue
            if topic is not None and topic not in article.topics:
                continue
            moment = article.published or saved_at
            if since is not None and moment < since:
                continue
            if until is not None and moment >= until:
                continue
            rows.append((moment, article))
        rows.sort(key=lambda row: (row[0], row[1].guid))
        return tuple(article for _, article in rows)

    def prune_older_than(self, keep_days: int) -> int:
        """Delete archived articles older than ``keep_days`` days; return how many were
        removed. Off unless a caller opts in -- the archive is durable, so nothing here
        runs by default. An article is dated by its ``published`` date, or by its archive
        timestamp when it has none (the same basis ``load`` orders by). Best-effort and
        re-runnable: a corrupt, forward-schema, or vanished file is left in place, never
        deleted on a guess.

        Raises:
            ValueError: ``keep_days`` is not a positive whole number of days.
            ArchiveError: a stored file could not be read or deleted (an I/O failure).
        """
        if keep_days < 1:
            raise ValueError(f"keep_days must be a positive number of days, got {keep_days}")
        cutoff = (datetime.now(UTC) - timedelta(days=keep_days)).strftime(_TIMESTAMP_FORMAT)
        removed = 0
        for path in self._dir.glob("*.json"):
            article, saved_at = _read_article(path)
            if article is None:
                continue   # corrupt / forward-schema: not ours to delete on a parse miss
            if (article.published or saved_at) >= cutoff:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                continue   # already gone (a concurrent prune) -- not an error
            except OSError as err:
                raise ArchiveError(f"could not delete {path}: {err}") from err
            removed += 1
        return removed


def _key(guid: str) -> str:
    """A filesystem-safe key for ``guid`` (a URL) -- its SHA-1 hex, so a slash- or
    query-laden guid becomes one flat filename."""
    return hashlib.sha1(guid.encode("utf-8")).hexdigest()


def _read_article(path: Path) -> tuple[Article | None, str]:
    """Rebuild ``(Article, saved_at)`` from a stored file; ``(None, "")`` when the file
    is corrupt or schema-drifted (read as absent). A genuine I/O error propagates."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, ""
    except OSError as err:
        raise ArchiveError(f"could not read {path}: {err}") from err
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        return None, ""
    if not isinstance(envelope, dict):
        return None, ""
    version = envelope.get("schema_version")
    if not (version is None or (isinstance(version, int) and version <= _SCHEMA_VERSION)):
        return None, ""   # a newer schema (or a corrupt version); read as absent, not fatal
    body = envelope.get("article")
    saved_at = envelope.get("saved_at")
    if not isinstance(body, dict) or not isinstance(saved_at, str):
        return None, ""
    try:
        title = str(body["title"])
        stored_region = body.get("region")
        region = (stored_region if isinstance(stored_region, str) and stored_region in REGIONS
                  else infer_region(title))   # a v1 file has no region -- infer it from the title
        article = Article(
            guid=str(body["guid"]), title=title, link=str(body["link"]),
            source_name=str(body["source_name"]), published=str(body["published"]),
            topics=tuple(str(t) for t in body.get("topics", ())), region=region,
            summary=str(body["summary"]), summary_model=str(body.get("summary_model", "")),
        )
    except (KeyError, TypeError):
        return None, ""
    return article, saved_at
