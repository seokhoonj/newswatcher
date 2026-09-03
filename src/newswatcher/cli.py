"""Command-line entry point.

Subcommands compose the library into user actions: ``add-topic`` / ``topics`` and
``add-source`` / ``sources`` manage the registries; ``recent`` previews a source
without storing; ``poll`` runs one collect-summarize-mail pass; ``watch`` repeats it
on an interval; ``articles`` queries the archive; ``digest`` renders an HTML digest
from the archive over a date span; ``heal`` checks and repairs crawl selectors;
``schedule`` registers the cron poll. The CLI is a thin shell -- parse,
wire, print -- and every deliberate failure surfaces as one stderr line with a
non-zero exit."""

from __future__ import annotations

import argparse
import functools
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from newswatcher import __version__, config
from newswatcher._atomic import write_text_atomic
from newswatcher._llm import DEFAULT_PROVIDER, validate_provider
from newswatcher.digest import send_digest
from newswatcher.digest_html import render_html
from newswatcher.errors import ArchiveError, ConfigError, DigestError, NewswatcherError
from newswatcher.feed import parse_feed
from newswatcher.heal import heal_empty_sources, heal_source
from newswatcher.http import default_gate, get, new_session
from newswatcher.lock import single_instance
from newswatcher.poll import poll_sources
from newswatcher.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    install_poll,
    parse_interval,
    poll_status,
    remove_poll,
)
from newswatcher.sources import Source, add_source, load_sources
from newswatcher.state import read_state, write_state
from newswatcher.store import FileStore
from newswatcher.stories import DEFAULT_THRESHOLD, Story, group_stories
from newswatcher.summarize import summarize_article
from newswatcher.topics import Topic, add_topic, load_topics

__all__ = ["main"]

_DIGEST_TO_ENV = "NEWSWATCHER_DIGEST_TO"
_DIGEST_PUSH_ENV = "NEWSWATCHER_DIGEST_PUSH"
_DEDUP_THRESHOLD_ENV = "NEWSWATCHER_DEDUP_THRESHOLD"
_ARCHIVE_KEEP_DAYS_ENV = "NEWSWATCHER_ARCHIVE_KEEP_DAYS"
_DIGEST_TITLE_ENV = "NEWSWATCHER_DIGEST_TITLE"
_DEFAULT_TITLE = "뉴스 브리핑"
_LLM_PROVIDER_ENV = "NEWSWATCHER_LLM_PROVIDER"
_LLM_MODEL_ENV = "NEWSWATCHER_LLM_MODEL"


def _resolve_llm_choice(args: argparse.Namespace) -> tuple[str, str | None]:
    """The LLM provider and model for this run: the ``--provider`` / ``--model`` flag
    wins, then the ``NEWSWATCHER_LLM_PROVIDER`` / ``NEWSWATCHER_LLM_MODEL`` setting, then the
    default provider and its default model. Same flag-over-setting precedence as ``--to``.

    Raises:
        LLMError: the resolved provider (from any source) is not one the backend knows --
            caught here so a typo fails fast with the valid choices, not deep in a poll.
    """
    provider = args.provider or config.setting(_LLM_PROVIDER_ENV) or DEFAULT_PROVIDER
    validate_provider(provider)   # fail fast on a typo, with the valid choices
    model = args.model or config.setting(_LLM_MODEL_ENV)
    return provider, model


def _resolve_dedup_threshold() -> float:
    """How similar two headlines must be (0.0-1.0) to collapse as one story: the
    ``NEWSWATCHER_DEDUP_THRESHOLD`` setting, or the built-in default when unset.

    Raises:
        ConfigError: the setting is present but not a number in ``[0, 1]`` -- caught here so
            a typo fails fast with the valid range, not silently disabling the collapse.
    """
    raw = config.setting(_DEDUP_THRESHOLD_ENV)
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        value = float(raw)
    except ValueError as err:
        raise ConfigError(
            f"{_DEDUP_THRESHOLD_ENV} must be a number between 0 and 1, got {raw!r}") from err
    if not 0.0 <= value <= 1.0:
        raise ConfigError(f"{_DEDUP_THRESHOLD_ENV} must be between 0 and 1, got {value}")
    return value


def _resolve_archive_keep_days() -> int | None:
    """How many days of archived articles to keep, or ``None`` to keep everything (the
    default). The archive is durable, so pruning is opt-in via
    ``NEWSWATCHER_ARCHIVE_KEEP_DAYS``; when set, a poll deletes archived articles older
    than that after delivering the digest.

    Raises:
        ConfigError: the setting is present but not a positive whole number of days --
            caught here so a typo fails fast rather than silently deleting nothing (or
            everything).
    """
    raw = config.setting(_ARCHIVE_KEEP_DAYS_ENV)
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError as err:
        raise ConfigError(
            f"{_ARCHIVE_KEEP_DAYS_ENV} must be a positive whole number of days, "
            f"got {raw!r}") from err
    if value < 1:
        raise ConfigError(f"{_ARCHIVE_KEEP_DAYS_ENV} must be at least 1 day, got {value}")
    return value


def main(argv: list[str] | None = None) -> int:
    """Run the chosen subcommand; return the process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        config.load_settings()
        args = _build_parser().parse_args(argv)
        exit_code: int = args.run(args)
        return exit_code
    except KeyboardInterrupt:
        print("newswatcher: cancelled", file=sys.stderr)
        return 130
    except NewswatcherError as err:
        print(f"newswatcher: {err}", file=sys.stderr)
        return 1
    except SystemExit as err:  # argparse errors (unknown command, bad flag), --version, -h
        code = err.code
        return code if isinstance(code, int) else (0 if code is None else 1)


# --- commands ------------------------------------------------------------------

def _run_add_topic(args: argparse.Namespace) -> int:
    topic = Topic(args.name, includes=tuple(args.include), excludes=tuple(args.exclude))
    if add_topic(topic):
        print(f"added topic {args.name!r}")
    else:
        print(f"topic {args.name!r} already exists")
    return 0


def _run_topics(args: argparse.Namespace) -> int:
    for topic in load_topics():
        parts = [topic.name]
        if topic.includes:
            parts.append(f"includes={list(topic.includes)}")
        if topic.excludes:
            parts.append(f"excludes={list(topic.excludes)}")
        print("  ".join(parts))
    return 0


def _run_add_source(args: argparse.Namespace) -> int:
    source = Source(
        args.name, kind=args.kind, url=args.url, topics=tuple(args.topic),
        region=args.region or "", keep_all=args.keep_all, item=args.item, title=args.title,
        link=args.link, date=args.date, body_selector=args.body_selector,
    )
    if add_source(source):   # validates; a crawl source without selectors raises SourceError
        print(f"added source {args.name!r}")
    else:
        print(f"source {args.name!r} already exists")
    return 0


def _run_sources(args: argparse.Namespace) -> int:
    for source in load_sources():
        parts = [source.name, f"[{source.kind}]", source.url]
        if source.topics:
            parts.append(f"topics={list(source.topics)}")
        if source.keep_all:
            parts.append("keep_all")
        print("  ".join(parts))
    return 0


def _run_recent(args: argparse.Namespace) -> int:
    gate = default_gate()
    items = parse_feed(get(args.url, gate), args.url)
    for item in items[: args.limit]:
        stamp = f"  {item.published}" if item.published else ""
        print(f"{item.title}{stamp}\n{item.link}\n")
    return 0


def _run_poll(args: argparse.Namespace) -> int:
    """Run one poll under a single-instance lock, so an overlapping cron or manual poll
    does not double-spend the LLM, mail duplicates, or race on the watermark. A poll
    already in progress is skipped (exit 0), not queued."""
    with single_instance("poll") as acquired:
        if not acquired:
            print("newswatcher: another poll is already running; skipping", file=sys.stderr)
            return 0
        return _poll_once(args)


def _poll_once(args: argparse.Namespace) -> int:
    sources = load_sources()
    topics = load_topics()
    gate = default_gate()
    state = read_state()
    store = None if args.no_store else FileStore()
    provider, model = _resolve_llm_choice(args)
    threshold = _resolve_dedup_threshold()   # validate up-front, before the poll spends the LLM
    keep_days = _resolve_archive_keep_days()   # ditto -- a bad value should not survive a poll
    summarize = functools.partial(summarize_article, provider=provider, model=model)
    with new_session() as session:   # one pooled connection for every fetch this poll
        report = poll_sources(sources, topics, gate=gate, state=state, store=store,
                              session=session, summarize=summarize)
        heal_notes = (
            heal_empty_sources(sources, gate=gate, state=state, session=session,
                               provider=provider, model=model)
            if not args.no_heal else ()
        )
    for name, reason in report.skipped:
        print(f"newswatcher: skipping {name}: {reason}", file=sys.stderr)
    stories = group_stories(report.collected, threshold=threshold)
    if not args.no_mail:
        email_to = args.to or config.setting(_DIGEST_TO_ENV)
        push_to = args.push or config.setting(_DIGEST_PUSH_ENV)
        if email_to or push_to:
            for failure in send_digest(stories, email_to=email_to,
                                       push_to=push_to, heal_notes=heal_notes):
                # A partial failure (one channel down, another delivered): report it, but do
                # not abort -- the watermark still advances, so the delivered channel is not
                # re-sent. Only an all-channel failure raises and withholds the watermark.
                print(f"newswatcher: {failure}", file=sys.stderr)
        else:
            print("newswatcher: no digest destination (set --to / NEWSWATCHER_DIGEST_TO for "
                  "email or --push / NEWSWATCHER_DIGEST_PUSH for chat); not sending",
                  file=sys.stderr)
    if args.html:
        _write_html_digest(stories, Path(args.html), title=_digest_title(args),
                           period_label="오늘")
        print(f"wrote HTML digest to {args.html}")
    # Persist the watermark only after the digest is out (or mailing was skipped): a
    # send failure then re-collects and re-sends next run rather than losing the digest.
    # The reverse window is the accepted cost of send-before-persist: if this atomic write
    # itself fails after a good send, next run re-sends the whole digest.
    write_state(state)
    # Prune only after the digest is out and the watermark is written, and only when the
    # user opted into a retention window -- the archive keeps everything by default. This
    # is best-effort cleanup after a delivered digest: an I/O error deleting an old file is
    # reported but does not fail the poll (the digest is already out and the watermark
    # written), and the next run retries the prune.
    if store is not None and keep_days is not None:
        try:
            removed = store.prune_older_than(keep_days)
        except ArchiveError as err:
            print(f"newswatcher: archive prune failed: {err}", file=sys.stderr)
        else:
            if removed:
                print(f"pruned {removed} archived article(s) older than {keep_days} day(s)")
    print(f"{len(report.collected)} new article(s)")
    return 0


def _run_watch(args: argparse.Namespace) -> int:
    every = args.every if args.every is not None else DEFAULT_INTERVAL_MINUTES
    # Screen the run's static config once, before the loop. A bad provider or dedup
    # threshold is permanent within the process (settings load once at startup; the
    # environment cannot change mid-run), so letting it raise here ends the watch with a
    # clear error instead of looping forever on the same failure while never delivering.
    # read_state is pre-flighted too so a corrupt state file fails fast at startup rather
    # than spinning the loop (the file is re-read each tick, so a mid-run fix still recovers).
    _resolve_llm_choice(args)
    _resolve_dedup_threshold()
    _resolve_archive_keep_days()
    read_state()
    print(f"watching every {every} min; Ctrl-C to stop", file=sys.stderr)
    next_tick = time.monotonic()
    while True:
        try:
            _run_poll(args)
        except NewswatcherError as err:
            # One transient failure (a fetch/LLM/mail blip) must not end the watch -- the
            # state was not written, so the next tick re-collects and re-sends. Permanent
            # config errors were screened out above the loop.
            print(f"newswatcher: {err}", file=sys.stderr)
        next_tick = max(next_tick + every * 60, time.monotonic())
        time.sleep(max(0.0, next_tick - time.monotonic()))   # a poll that overran sleeps 0


def _run_articles(args: argparse.Namespace) -> int:
    articles = FileStore().load(topic=args.topic, since=args.since, until=args.until)
    for article in articles:
        stamp = f"  {article.published}" if article.published else ""
        print(f"[{', '.join(article.topics)}] {article.title}{stamp}\n"
              f"  {article.summary}\n  {article.link}\n")
    return 0


def _run_digest(args: argparse.Namespace) -> int:
    """Render an HTML digest from the archive over a date span. Reads the durable archive
    rather than a live poll -- so a weekly or monthly view is available long after the
    source feeds have rolled over -- collapses cross-source duplicates, and writes one
    self-contained HTML page."""
    since, until, label = _resolve_digest_span(args)
    threshold = _resolve_dedup_threshold()
    articles = FileStore().load(topic=args.topic, since=since, until=until)
    stories = group_stories(articles, threshold=threshold)
    _write_html_digest(stories, Path(args.html), title=_digest_title(args), period_label=label)
    print(f"wrote {len(stories)} stor{'y' if len(stories) == 1 else 'ies'} "
          f"({label}) to {args.html}")
    return 0


def _resolve_digest_span(args: argparse.Namespace) -> tuple[str | None, str | None, str]:
    """The ``(since, until, label)`` for a digest span. Explicit ``--since`` / ``--until``
    win; otherwise ``--range`` maps to a rolling window ending now (compared against the
    archive's ISO-8601 timestamps, so a window bound is itself an ISO-8601 instant)."""
    if args.since or args.until:
        return args.since, args.until, f"{args.since or '처음'} ~ {args.until or '지금'}"
    windows = {"day": (1, "지난 24시간"), "week": (7, "지난 7일"), "month": (30, "지난 30일")}
    days, label = windows[args.range_]
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return since, None, label


def _digest_title(args: argparse.Namespace) -> str:
    """The digest heading: ``--title``, else the ``NEWSWATCHER_DIGEST_TITLE`` setting, else
    a generic default."""
    return args.title or config.setting(_DIGEST_TITLE_ENV) or _DEFAULT_TITLE


def _write_html_digest(stories: tuple[Story, ...], path: Path, *,
                       title: str, period_label: str) -> None:
    """Render ``stories`` to an HTML page and write it to ``path`` atomically.

    Raises:
        DigestError: the page could not be written (propagated from the atomic write).
    """
    page = render_html(stories, title=title, period_label=period_label,
                       generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"))
    write_text_atomic(path, page, DigestError)


def _run_heal(args: argparse.Namespace) -> int:
    gate = default_gate()
    provider, model = _resolve_llm_choice(args)
    for source in load_sources():
        if source.kind != "crawl":
            continue
        try:
            result = heal_source(source, gate=gate, should_apply=not args.dry_run,
                                 provider=provider, model=model)
        except NewswatcherError as err:
            # One source's failure must not stop the rest (the package invariant).
            print(f"newswatcher: healing {source.name} failed: {err}", file=sys.stderr)
            continue
        if result is not None:
            print(result.note)
    return 0


def _run_schedule(args: argparse.Namespace) -> int:
    if args.action == "install":
        every = args.every if args.every is not None else DEFAULT_INTERVAL_MINUTES
        print(f"installed: {install_poll(every)}")
    elif args.action == "remove":
        print("removed the poll job" if remove_poll() else "no poll job was installed")
    else:
        status = poll_status()
        print(status if status else "not installed")
    return 0


# --- argument parser -----------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="newswatcher",
                                     description="Watch news sources, match topics, mail a digest.")
    parser.add_argument("--version", action="version", version=f"newswatcher {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    add_topic_cmd = sub.add_parser("add-topic", help="define a topic")
    add_topic_cmd.add_argument("name")
    add_topic_cmd.add_argument("--include", nargs="*", default=[], metavar="WORD")
    add_topic_cmd.add_argument("--exclude", nargs="*", default=[], metavar="WORD")
    add_topic_cmd.set_defaults(run=_run_add_topic)

    topics = sub.add_parser("topics", help="list topics")
    topics.set_defaults(run=_run_topics)

    add_source_cmd = sub.add_parser("add-source", help="register a source")
    add_source_cmd.add_argument("name")
    add_source_cmd.add_argument("url")
    add_source_cmd.add_argument("--kind", choices=("rss", "crawl"), default="rss")
    add_source_cmd.add_argument("--region", choices=("kr", "intl"), default=None,
                                help="kr (domestic) or intl (overseas); inferred from the "
                                     "article title language when omitted")
    add_source_cmd.add_argument("--topic", action="append", default=[], metavar="NAME",
                                help="a topic this source subscribes to (repeatable)")
    add_source_cmd.add_argument("--keep-all", action="store_true", dest="keep_all",
                                help="keep every article (a trade paper); skip the keyword filter")
    add_source_cmd.add_argument("--item", default=None, help="crawl: article-row selector")
    add_source_cmd.add_argument("--title", default=None, help="crawl: title selector")
    add_source_cmd.add_argument("--link", default=None, help="crawl: link selector (css@href)")
    add_source_cmd.add_argument("--date", default=None, help="crawl: date selector (optional)")
    add_source_cmd.add_argument("--body-selector", default=None, dest="body_selector",
                                help="override generic body extraction for this source")
    add_source_cmd.set_defaults(run=_run_add_source)

    sources = sub.add_parser("sources", help="list sources")
    sources.set_defaults(run=_run_sources)

    recent = sub.add_parser("recent", help="preview a feed URL (no store)")
    recent.add_argument("url")
    recent.add_argument("--limit", type=int, default=10)
    recent.set_defaults(run=_run_recent)

    poll = sub.add_parser("poll", help="collect, summarize, and mail once")
    _add_poll_flags(poll)
    poll.set_defaults(run=_run_poll)

    watch = sub.add_parser("watch", help="poll repeatedly in the foreground")
    watch.add_argument("--every", type=_interval, default=None, metavar="MINUTES")
    _add_poll_flags(watch)
    watch.set_defaults(run=_run_watch)

    articles = sub.add_parser("articles", help="list archived articles")
    articles.add_argument("--topic", default=None)
    articles.add_argument("--since", default=None, metavar="DATE")
    articles.add_argument("--until", default=None, metavar="DATE")
    articles.set_defaults(run=_run_articles)

    digest = sub.add_parser("digest", help="render an HTML digest from the archive")
    digest.add_argument("--html", required=True, metavar="PATH",
                        help="write the digest HTML page to this file")
    digest.add_argument("--range", choices=("day", "week", "month"), default="week",
                        dest="range_", help="rolling window to cover (default: week)")
    digest.add_argument("--since", default=None, metavar="DATE",
                        help="ISO date lower bound (overrides --range)")
    digest.add_argument("--until", default=None, metavar="DATE", help="ISO date upper bound")
    digest.add_argument("--topic", default=None, help="limit to one topic tag")
    digest.add_argument("--title", default=None, help="digest heading")
    digest.set_defaults(run=_run_digest)

    heal = sub.add_parser("heal", help="check and repair crawl selectors")
    heal.add_argument("--dry-run", action="store_true", dest="dry_run")
    _add_llm_flags(heal)
    heal.set_defaults(run=_run_heal)

    schedule = sub.add_parser("schedule", help="register the recurring poll with the OS scheduler")
    schedule.add_argument("action", choices=("install", "remove", "status"))
    schedule.add_argument("--every", type=_interval, default=None, metavar="MINUTES")
    schedule.set_defaults(run=_run_schedule)

    return parser


def _add_poll_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--to", default=None, help="email digest recipient (mailmail address or alias)")
    parser.add_argument("--push", default=None, metavar="ROUTE",
                        help="also send the digest to a pushpush chat route")
    parser.add_argument("--no-mail", action="store_true", dest="no_mail",
                        help="collect and archive but do not send the digest (email or chat)")
    parser.add_argument("--no-store", action="store_true", dest="no_store",
                        help="do not archive collected articles")
    parser.add_argument("--no-heal", action="store_true", dest="no_heal",
                        help="do not run selector healing this poll")
    parser.add_argument("--html", default=None, metavar="PATH",
                        help="also write this poll's digest as an HTML page to PATH")
    parser.add_argument("--title", default=None,
                        help="digest heading (default: NEWSWATCHER_DIGEST_TITLE or a generic title)")
    _add_llm_flags(parser)


def _add_llm_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=None,
                        help=f"LLM provider for summaries and healing (default {DEFAULT_PROVIDER})")
    parser.add_argument("--model", default=None, help="LLM model for the chosen provider")


def _interval(text: str) -> int:
    try:
        return parse_interval(text)
    except NewswatcherError as err:
        raise argparse.ArgumentTypeError(str(err)) from err
