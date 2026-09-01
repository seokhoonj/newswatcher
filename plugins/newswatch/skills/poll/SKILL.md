---
name: poll
description: "Run one newswatch poll: collect new articles from your configured RSS/crawl sources, match them to your topics, summarize with an LLM, and deliver one topic-grouped digest by email or chat. Holds no logic of its own -- it calls the newswatch package's CLI (`newswatch`) and relays the result. Duplicate stories from several outlets collapse into one entry. Trigger phrases: run my newswatch poll, check the news, poll my feeds, get my news digest, collect news now, 뉴스 확인해줘, 뉴스 폴링, 다이제스트 돌려줘, 뉴스 수집해줘."
---

# newswatch — poll and deliver the topic digest

Run **collect -> match -> summarize -> deliver** once over the user's configured sources.
The collecting, matching, summarizing, and delivery all live in the newswatch package (on
PyPI); this skill is a thin wrapper that calls its CLI and relays the outcome. A missing
digest recipient, an LLM key/credit problem, a dead source, and the like come back from the
CLI as a one-line `newswatch: <message>` -- relay that as-is rather than throwing a stack
trace at the user.

newswatch is a *configured* tool: topics and sources are registered once (in
`topics.toml` / `sources.toml`, or via `newswatch add-topic` / `add-source`), then each poll
reuses them. So before polling, check that at least one topic and one source exist.

## Prerequisite

This plugin calls the `newswatch` CLI, so it must be installed first:

```
pipx install newswatch        # or: pip install newswatch
```

That puts the `newswatch` command on PATH. **newswatch finds its own key** -- it reads the
provider key (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `CLAUDE_API_KEY`) from
`~/.config/newswatch/credentials.json` (or the environment), so this skill never has to pull
a key out and pass it. Gemini's free tier is the default provider. Never print a key value
anywhere.

Delivery also needs a destination: an email recipient (`NEWSWATCH_DIGEST_TO`, or `--to`) via
the mailmail package, and/or a chat route (`NEWSWATCH_DIGEST_PUSH`, or `--push`) via the
pushpush package. Both are installed with newswatch; a pushpush route is configured with
pushpush's own CLI.

## Running

Call `newswatch` from PATH with the `poll` subcommand:

```
newswatch poll [options]
```

Options (`newswatch poll --help` is the source of truth for exact defaults):
- `--to ADDRESS` — email recipient for this run (a mailmail address or alias). Overrides `NEWSWATCH_DIGEST_TO`.
- `--push ROUTE` — also deliver to a pushpush chat route. Overrides `NEWSWATCH_DIGEST_PUSH`.
- `--no-mail` — collect, summarize, and archive but do NOT deliver (use this to just *look* at what is new).
- `--no-store` — do not archive the collected articles this run.
- `--no-heal` — skip the crawl-selector self-repair pass this run.
- `--provider claude|openai|gemini|...` / `--model <id>` — override the LLM vendor/model (default gemini).

## Procedure

1. **Confirm it is configured.** Run `newswatch topics` and `newswatch sources`. If either
   is empty, do NOT invent topics/sources -- explain that newswatch needs at least one topic
   and one source, and help the user add them:

   ```bash
   newswatch add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
   newswatch add-source "BBC" https://feeds.bbci.co.uk/news/world/rss.xml --kind rss --topic markets
   ```

   The repo's `docs/korean-news-rss.md` and `docs/world-news-rss.md` hold verified feed URLs
   to pick from. Keywords match in the feed's own language (English keywords for an English
   feed, Korean for a Korean feed).

2. **Decide delivery.**
   - The user wants the digest *delivered* (the normal case): run plain `newswatch poll`.
     This needs a destination configured (`NEWSWATCH_DIGEST_TO` / `--to`, or
     `NEWSWATCH_DIGEST_PUSH` / `--push`); pass `--to`/`--push` if the user names one.
   - The user just wants to *see* what is new here, without sending: run
     `newswatch poll --no-mail`, then show the fresh archive inline with
     `newswatch articles --since <today's date, YYYY-MM-DD>` (title / summary / link per entry).

3. **Run the poll** and relay the outcome: the `N new article(s)` line, any
   `newswatch: skipping <source>: <reason>` lines, and whether the digest was delivered. A
   poll can take a while (it fetches every source and calls the LLM per article) -- that is
   normal.

4. **Error handling.** When the CLI exits non-zero, relay the one-line `newswatch: <message>`
   as-is. Common ones:
   - `command not found: newswatch` -> the package is not installed. Point the user at
     `pipx install newswatch` (or `pip install newswatch`).
   - `no digest destination ...` -> no recipient is set. Offer `--to you@example.com` or a
     `--push <route>`, or set `NEWSWATCH_DIGEST_TO` / `NEWSWATCH_DIGEST_PUSH`. (Or run with
     `--no-mail` to just collect.)
   - `no API key` / `insufficient_quota` / `429` -> the provider key is missing from
     `~/.config/newswatch/credentials.json`, or its credits are exhausted. Point the user at
     the vendor console (Google AI Studio / OpenAI / Claude).
   - `another poll is already running; skipping` -> a scheduled or manual poll holds the
     single-instance lock. Not an error -- newswatch exits cleanly rather than double-running.
   - `NEWSWATCH_DEDUP_THRESHOLD must be ...` -> a malformed dedup-threshold setting; it must
     be a number in `[0, 1]`.

## What this skill does not do

- It does not re-implement collection, topic matching, summarizing, or delivery here (the
  package does); it always calls the CLI.
- It never prints, logs, or includes an API key value in output.
- It does not invent topics or sources -- it polls what the user has configured, and helps
  them add more only on request.

## See also

- `newswatch recent <url>` — preview a feed's latest items (no store) before adding it.
- `newswatch articles [--topic NAME] [--since DATE] [--until DATE]` — query the archive.
- `newswatch watch [--every N]` — repeat the poll on an interval in the foreground.
- `newswatch schedule install|status|remove [--every N]` — register a recurring poll with the
  OS scheduler (cron on Linux/macOS, schtasks on Windows).
- `newswatch heal` — check and repair crawl selectors that stopped matching.
