---
name: poll
description: "Run one newswatcher poll: collect new articles from your configured RSS/crawl sources, match them to your topics, summarize with an LLM, and deliver one topic-grouped digest by email or chat. Holds no logic of its own -- it calls the newswatcher package's CLI (`newswatcher`) and relays the result. Duplicate stories from several outlets collapse into one entry. Trigger phrases: run my newswatcher poll, check the news, poll my feeds, get my news digest, collect news now, 뉴스 확인해줘, 뉴스 폴링, 다이제스트 돌려줘, 뉴스 수집해줘."
---

# newswatcher — poll and deliver the topic digest

Run **collect -> match -> summarize -> deliver** once over the user's configured sources.
The collecting, matching, summarizing, and delivery all live in the newswatcher package (on
PyPI); this skill is a thin wrapper that calls its CLI and relays the outcome. A missing
digest recipient, an LLM key/credit problem, a dead source, and the like come back from the
CLI as a one-line `newswatcher: <message>` -- relay that as-is rather than throwing a stack
trace at the user.

newswatcher is a *configured* tool: topics and sources are registered once (in
`topics.toml` / `sources.toml`, or via `newswatcher add-topic` / `add-source`), then each poll
reuses them. So before polling, check that at least one topic and one source exist.

## Prerequisite

This plugin calls the `newswatcher` CLI, so it must be installed first:

```
pipx install newswatcher        # or: pip install newswatcher
```

That puts the `newswatcher` command on PATH. **newswatcher finds its own key** -- it reads the
provider key (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `CLAUDE_API_KEY`) from
`~/.config/newswatcher/credentials.json` (or the environment), so this skill never has to pull
a key out and pass it. Gemini's free tier is the default provider. Never print a key value
anywhere.

Delivery also needs a destination: an email recipient (`NEWSWATCHER_DIGEST_TO`, or `--to`) via
the mailmail package, and/or a chat route (`NEWSWATCHER_DIGEST_PUSH`, or `--push`) via the
pushpush package. Both are installed with newswatcher; a pushpush route is configured with
pushpush's own CLI.

## Running

Call `newswatcher` from PATH with the `poll` subcommand:

```
newswatcher poll [options]
```

Options (`newswatcher poll --help` is the source of truth for exact defaults):
- `--to ADDRESS` — email recipient for this run (a mailmail address or alias). Overrides `NEWSWATCHER_DIGEST_TO`.
- `--push ROUTE` — also deliver to a pushpush chat route. Overrides `NEWSWATCHER_DIGEST_PUSH`.
- `--no-mail` — collect, summarize, and archive but do NOT deliver (use this to just *look* at what is new).
- `--no-store` — do not archive the collected articles this run.
- `--no-heal` — skip the crawl-selector self-repair pass this run.
- `--provider claude|openai|gemini|...` / `--model <id>` — override the LLM vendor/model (default gemini).

## Procedure

1. **Confirm it is configured.** Run `newswatcher topics` and `newswatcher sources`. If either
   is empty, do NOT invent topics/sources -- explain that newswatcher needs at least one topic
   and one source, and help the user add them:

   ```bash
   newswatcher add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
   newswatcher add-source "BBC" https://feeds.bbci.co.uk/news/world/rss.xml --kind rss --topic markets
   ```

   The repo's `docs/korean-news-rss.md` and `docs/world-news-rss.md` hold verified feed URLs
   to pick from. Keywords match in the feed's own language (English keywords for an English
   feed, Korean for a Korean feed).

2. **Decide delivery.**
   - The user wants the digest *delivered* (the normal case): run plain `newswatcher poll`.
     This needs a destination configured (`NEWSWATCHER_DIGEST_TO` / `--to`, or
     `NEWSWATCHER_DIGEST_PUSH` / `--push`); pass `--to`/`--push` if the user names one.
   - The user just wants to *see* what is new here, without sending: run
     `newswatcher poll --no-mail`, then show the fresh archive inline with
     `newswatcher articles --since <today's date, YYYY-MM-DD>` (title / summary / link per entry).

3. **Run the poll** and relay the outcome: the `N new article(s)` line, any
   `newswatcher: skipping <source>: <reason>` lines, and whether the digest was delivered. A
   poll can take a while (it fetches every source and calls the LLM per article) -- that is
   normal.

4. **Error handling.** When the CLI exits non-zero, relay the one-line `newswatcher: <message>`
   as-is. Common ones:
   - `command not found: newswatcher` -> the package is not installed. Point the user at
     `pipx install newswatcher` (or `pip install newswatcher`).
   - `no digest destination ...` -> no recipient is set. Offer `--to you@example.com` or a
     `--push <route>`, or set `NEWSWATCHER_DIGEST_TO` / `NEWSWATCHER_DIGEST_PUSH`. (Or run with
     `--no-mail` to just collect.)
   - `no API key` / `insufficient_quota` / `429` -> the provider key is missing from
     `~/.config/newswatcher/credentials.json`, or its credits are exhausted. Point the user at
     the vendor console (Google AI Studio / OpenAI / Claude).
   - `another poll is already running; skipping` -> a scheduled or manual poll holds the
     single-instance lock. Not an error -- newswatcher exits cleanly rather than double-running.
   - `NEWSWATCHER_DEDUP_THRESHOLD must be ...` -> a malformed dedup-threshold setting; it must
     be a number in `[0, 1]`.

## What this skill does not do

- It does not re-implement collection, topic matching, summarizing, or delivery here (the
  package does); it always calls the CLI.
- It never prints, logs, or includes an API key value in output.
- It does not invent topics or sources -- it polls what the user has configured, and helps
  them add more only on request.

## See also

- `newswatcher recent <url>` — preview a feed's latest items (no store) before adding it.
- `newswatcher articles [--topic NAME] [--since DATE] [--until DATE]` — query the archive.
- `newswatcher watch [--every N]` — repeat the poll on an interval in the foreground.
- `newswatcher schedule install|status|remove [--every N]` — register a recurring poll with the
  OS scheduler (cron on Linux/macOS, schtasks on Windows).
- `newswatcher heal` — check and repair crawl selectors that stopped matching.
