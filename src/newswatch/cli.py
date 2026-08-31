"""Command-line entry point.

Subcommands compose the library into user actions: ``add-topic`` / ``topics`` and
``add-source`` / ``sources`` manage the registries; ``recent`` previews a source
without storing; ``poll`` runs one collect-summarize-mail pass; ``watch`` repeats it
on an interval; ``articles`` queries the archive; ``heal`` checks and repairs crawl
selectors; ``schedule`` registers the cron poll. The CLI is a thin shell -- parse,
wire, print -- and every deliberate failure surfaces as one stderr line with a
non-zero exit."""

from __future__ import annotations

import argparse
import functools
import sys
import time

from newswatch import __version__, config
from newswatch._llm import DEFAULT_PROVIDER, validate_provider
from newswatch.digest import send_digest
from newswatch.errors import NewswatchError
from newswatch.feed import parse_feed
from newswatch.heal import heal_empty_sources, heal_source
from newswatch.http import get, new_session
from newswatch.lock import single_instance
from newswatch.poll import poll_sources
from newswatch.robots import default_gate
from newswatch.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    install_poll,
    parse_interval,
    poll_status,
    remove_poll,
)
from newswatch.sources import Source, add_source, load_sources
from newswatch.state import read_state, write_state
from newswatch.store import FileStore
from newswatch.summarize import summarize_article
from newswatch.topics import Topic, add_topic, load_topics

__all__ = ["main"]

_DIGEST_TO_ENV = "NEWSWATCH_DIGEST_TO"
_LLM_PROVIDER_ENV = "NEWSWATCH_LLM_PROVIDER"
_LLM_MODEL_ENV = "NEWSWATCH_LLM_MODEL"


def _resolve_llm_choice(args: argparse.Namespace) -> tuple[str, str | None]:
    """The LLM provider and model for this run: the ``--provider`` / ``--model`` flag
    wins, then the ``NEWSWATCH_LLM_PROVIDER`` / ``NEWSWATCH_LLM_MODEL`` setting, then the
    default provider and its default model. Same flag-over-setting precedence as ``--to``.

    Raises:
        LLMError: the resolved provider (from any source) is not one the backend knows --
            caught here so a typo fails fast with the valid choices, not deep in a poll.
    """
    provider = args.provider or config.setting(_LLM_PROVIDER_ENV) or DEFAULT_PROVIDER
    validate_provider(provider)   # fail fast on a typo, with the valid choices
    model = args.model or config.setting(_LLM_MODEL_ENV)
    return provider, model


def main(argv: list[str] | None = None) -> int:
    """Run the chosen subcommand; return the process exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        config.load_settings()
        args = _build_parser().parse_args(argv)
        exit_code: int = args.run(args)
        return exit_code
    except KeyboardInterrupt:
        print("newswatch: cancelled", file=sys.stderr)
        return 130
    except NewswatchError as err:
        print(f"newswatch: {err}", file=sys.stderr)
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
        keep_all=args.keep_all, item=args.item, title=args.title,
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
            print("newswatch: another poll is already running; skipping", file=sys.stderr)
            return 0
        return _poll_once(args)


def _poll_once(args: argparse.Namespace) -> int:
    sources = load_sources()
    topics = load_topics()
    gate = default_gate()
    state = read_state()
    store = None if args.no_store else FileStore()
    provider, model = _resolve_llm_choice(args)
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
        print(f"newswatch: skipping {name}: {reason}", file=sys.stderr)
    if not args.no_mail:
        to = args.to or config.setting(_DIGEST_TO_ENV)
        if to:
            send_digest(report.collected, to=to, heal_notes=heal_notes)
        else:
            print("newswatch: no digest recipient (set --to or NEWSWATCH_DIGEST_TO); "
                  "not mailing", file=sys.stderr)
    # Persist the watermark only after the digest is out (or mailing was skipped): a
    # send failure then re-collects and re-sends next run rather than losing the digest.
    write_state(state)
    print(f"{len(report.collected)} new article(s)")
    return 0


def _run_watch(args: argparse.Namespace) -> int:
    every = args.every if args.every is not None else DEFAULT_INTERVAL_MINUTES
    print(f"watching every {every} min; Ctrl-C to stop", file=sys.stderr)
    next_tick = time.monotonic()
    while True:
        try:
            _run_poll(args)
        except NewswatchError as err:
            # One transient failure (a mail/LLM/config error) must not end the watch --
            # the state was not written, so the next tick re-collects and re-sends.
            print(f"newswatch: {err}", file=sys.stderr)
        next_tick = max(next_tick + every * 60, time.monotonic())
        time.sleep(max(0.0, next_tick - time.monotonic()))   # a poll that overran sleeps 0


def _run_articles(args: argparse.Namespace) -> int:
    articles = FileStore().load(topic=args.topic, since=args.since, until=args.until)
    for article in articles:
        stamp = f"  {article.published}" if article.published else ""
        print(f"[{', '.join(article.topics)}] {article.title}{stamp}\n"
              f"  {article.summary}\n  {article.link}\n")
    return 0


def _run_heal(args: argparse.Namespace) -> int:
    gate = default_gate()
    provider, model = _resolve_llm_choice(args)
    for source in load_sources():
        if source.kind != "crawl":
            continue
        try:
            result = heal_source(source, gate=gate, apply=not args.dry_run,
                                 provider=provider, model=model)
        except NewswatchError as err:
            # One source's failure must not stop the rest (the package invariant).
            print(f"newswatch: healing {source.name} failed: {err}", file=sys.stderr)
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
    parser = argparse.ArgumentParser(prog="newswatch",
                                     description="Watch news sources, match topics, mail a digest.")
    parser.add_argument("--version", action="version", version=f"newswatch {__version__}")
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

    heal = sub.add_parser("heal", help="check and repair crawl selectors")
    heal.add_argument("--dry-run", action="store_true", dest="dry_run")
    _add_llm_flags(heal)
    heal.set_defaults(run=_run_heal)

    schedule = sub.add_parser("schedule", help="register the recurring poll with cron")
    schedule.add_argument("action", choices=("install", "remove", "status"))
    schedule.add_argument("--every", type=_interval, default=None, metavar="MINUTES")
    schedule.set_defaults(run=_run_schedule)

    return parser


def _add_poll_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--to", default=None, help="digest recipient (mailmail address or alias)")
    parser.add_argument("--no-mail", action="store_true", dest="no_mail",
                        help="collect and archive but do not send the digest")
    parser.add_argument("--no-store", action="store_true", dest="no_store",
                        help="do not archive collected articles")
    parser.add_argument("--no-heal", action="store_true", dest="no_heal",
                        help="do not run selector healing this poll")
    _add_llm_flags(parser)


def _add_llm_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--provider", default=None,
                        help=f"LLM provider for summaries and healing (default {DEFAULT_PROVIDER})")
    parser.add_argument("--model", default=None, help="LLM model for the chosen provider")


def _interval(text: str) -> int:
    try:
        return parse_interval(text)
    except NewswatchError as err:
        raise argparse.ArgumentTypeError(str(err)) from err
