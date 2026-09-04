# newswatcher

**English** | [한국어](README.ko.md)

newswatcher watches RSS feeds and robots-permitted listing pages, matches new
articles against topics you define, summarizes the matches with an LLM, and
sends one topic-grouped digest by email, chat, or both. Several outlets covering
the same story collapse into a single entry. The topics are yours to define, so
the same tool tracks a stock ticker, a technology, a policy beat, or any subject
a feed covers.

## Install

newswatcher requires Python 3.11 or newer.

```sh
pip install newswatcher
```

## Quickstart

Define a topic, register an RSS source, provide a digest recipient and the API
key for the default Gemini LLM provider, then run one poll:

```sh
newswatcher add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
newswatcher add-source korea-herald https://www.koreaherald.com/rss/newsAll \
  --kind rss --topic markets
export NEWSWATCHER_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatcher poll
```

A topic matches on the feed's own language, so pair the keywords with the feed:
English keywords for an English feed, Korean keywords for a Korean feed.

Use `newswatcher topics` and `newswatcher sources` to inspect the registries. Run
`newswatcher --help` or `newswatcher <command> --help` for all commands and options.

## Commands

Run `newswatcher --help` or `newswatcher <command> --help` for every option;
`newswatcher --version` prints the version.

| Command | What it does |
|---------|--------------|
| `add-topic <name> [--include WORD...] [--exclude WORD...]` | Define a topic filter. |
| `topics` | List the defined topics. |
| `add-source <name> <url> [--kind rss\|crawl] [--topic NAME]... [--keep-all]` | Register a source. A crawl source also takes selectors — `--item --title --link` (required), `--date --body-selector` (optional). `--keep-all` keeps every article without keyword filtering. |
| `sources` | List the registered sources. |
| `recent <url> [--limit N]` | Preview a feed's latest items without storing, to check it before adding. |
| `poll` | Collect → summarize → send, once. Options: `--to ADDRESS`, `--push ROUTE`, `--no-mail`, `--no-store`, `--no-heal`, `--provider` / `--model`. |
| `watch [--every N]` | The same as `poll`, repeated on an interval in the foreground. |
| `articles [--topic NAME] [--since DATE] [--until DATE]` | List archived articles. |
| `heal [--dry-run] [--provider P] [--model M]` | Check and repair crawl selectors that stopped matching. |
| `schedule install\|status\|remove [--every N]` | Register the recurring poll with the OS scheduler. |

## Delivery

The digest is sent by email, to a chat channel, or both — set one or both destinations.
Both channels are handled by companion packages that install alongside newswatcher.

- Email goes through the mailmail package: `--to ADDRESS` or the `NEWSWATCHER_DIGEST_TO` setting (a
  mailmail address or address-book alias).
- Chat goes through the pushpush package: `--push ROUTE` or the `NEWSWATCHER_DIGEST_PUSH` setting,
  naming a route you configured in pushpush (Telegram, Slack, or Discord). The digest is
  sent as one markdown message.

Configure a pushpush route with pushpush's
own CLI before using `--push`.

## News feeds

Any valid RSS/Atom feed works as a source. A representative set of verified
Korean feeds is below; the full list, grouped by section and marked with which
were live at verification, is in [docs/korean-news-rss.md](docs/korean-news-rss.md).
A site with no feed can still be followed with a `--kind crawl` source.

| Outlet | Beat | Feed URL |
|--------|------|----------|
| 연합뉴스 (Yonhap) | wire | `https://www.yna.co.kr/rss/news.xml` |
| 한국경제 (Hankyung) | economy | `https://www.hankyung.com/feed/all-news` |
| 조선비즈 (ChosunBiz) | economy | `https://biz.chosun.com/arc/outboundfeeds/rss/?outputType=xml` |
| 매일경제 (Maeil) | economy | `https://www.mk.co.kr/rss/30000001/` |
| 이데일리 (Edaily) | economy | `http://rss.edaily.co.kr/edaily_news.xml` |
| 머니투데이 (MoneyToday) | economy | `http://rss.mt.co.kr/mt_news.xml` |
| 전자신문 (ETNews) | tech | `https://rss.etnews.com/Section901.xml` |
| 지디넷코리아 (ZDNet Korea) | tech | `https://feeds.feedburner.com/zdkorea` |
| The Korea Herald | English | `https://www.koreaherald.com/rss/newsAll` |
| The Korea Times | English | `https://feed.koreatimes.co.kr/k/allnews.xml` |

A representative set of verified international (English) feeds is below; the full
list, grouped by category and marked with which outlets paywall the article body,
is in [docs/world-news-rss.md](docs/world-news-rss.md). Pair these with English
topic keywords.

| Outlet | Beat | Feed URL |
|--------|------|----------|
| BBC News | wire | `https://feeds.bbci.co.uk/news/world/rss.xml` |
| The Guardian | wire | `https://www.theguardian.com/world/rss` |
| Al Jazeera | wire | `https://www.aljazeera.com/xml/rss/all.xml` |
| The New York Times | world | `https://rss.nytimes.com/services/xml/rss/nyt/World.xml` |
| CNBC | economy | `https://www.cnbc.com/id/100003114/device/rss/rss.html` |
| MarketWatch | economy | `http://feeds.marketwatch.com/marketwatch/topstories/` |
| TechCrunch | tech | `https://techcrunch.com/feed/` |
| The Verge | tech | `https://www.theverge.com/rss/index.xml` |
| Nature | science | `https://www.nature.com/nature.rss` |

## Configuration files

newswatcher stores hand-edited configuration under
`$XDG_CONFIG_HOME/newswatcher`, or `~/.config/newswatcher` when
`XDG_CONFIG_HOME` is unset. The CLI writes the same files, so CLI and manual
configuration can be mixed.

`topics.toml` contains topic filters. An article matches when its title or feed
summary contains any include keyword and no exclude keyword. An empty
`includes` list matches every article.

```toml
[[topic]]
name = "markets"
includes = ["stocks", "Fed", "interest rate", "earnings"]
excludes = ["sports"]

[[topic]]
name = "semiconductors"
includes = ["chip", "foundry", "HBM", "TSMC", "Nvidia"]
```

`sources.toml` contains RSS or crawl sources. `topics` selects the topic filters
applied to a source. Set `keep_all = true` for a source whose every article
should be retained without keyword filtering.

```toml
[[source]]
name = "korea-herald"
kind = "rss"
url = "https://www.koreaherald.com/rss/newsAll"
topics = ["markets", "semiconductors"]

[[source]]
name = "exchange-notices"
kind = "crawl"
url = "https://example.com/markets/notices"
topics = ["markets"]
item = "article.news-item"
title = "h2"
link = "a@href"
date = "time"
body_selector = "main article"
```

The `item`, `title`, and `link` selectors are required for crawl sources;
`date` and `body_selector` are optional. The link selector uses the
`css@attribute` form when the URL is stored in an attribute.

Non-secret settings can also be placed in `config.toml`. Environment variables
take precedence over corresponding settings there. For example,
`NEWSWATCHER_DIGEST_TO` maps to `digest_to`, and `NEWSWATCHER_DIGEST_PUSH` to `digest_push`.
`NEWSWATCHER_DEDUP_THRESHOLD` (`dedup_threshold`, 0.0–1.0, default 0.5) sets how alike two
headlines must be to collapse as one story — raise it to merge less, lower it to merge
more. The article archive and run state use
the XDG data and state directories; `NEWSWATCHER_DATA_DIR` and
`NEWSWATCHER_STATE_DIR` can override them. The archive deletes nothing by default; to
prune old records, set `NEWSWATCHER_ARCHIVE_KEEP_DAYS` (`archive_keep_days`, a positive
integer) and each poll removes archived articles older than that after the digest is
sent. Leaving it unset keeps everything (this deletion is irreversible, so enable it
deliberately).

## Provider keys and model

An LLM provider key is a secret, so it lives apart from the settings, in
`credentials.json` under the same config directory — a flat JSON map keyed by the
provider's standard environment-variable name:

```json
{
  "GEMINI_API_KEY": "...",
  "OPENAI_API_KEY": "...",
  "CLAUDE_API_KEY": "..."
}
```

Each key is also read from that same environment variable, which takes precedence,
so a one-off run can supply a key without editing the file.

newswatcher summarizes with Gemini's free tier by default. Choose another provider,
and optionally a specific model, with `--provider` / `--model`, or persistently
with the `NEWSWATCHER_LLM_PROVIDER` / `NEWSWATCHER_LLM_MODEL` settings (`llm_provider`
and `llm_model` in `config.toml`):

```sh
newswatcher poll --provider claude --model claude-sonnet-5
export NEWSWATCHER_LLM_PROVIDER=openai
```

## Responsible collection

Every feed, listing-page, and article request is checked against the site's
robots policy before it is sent, and newswatcher identifies itself with its user
agent. A disallowed URL is not fetched. The durable archive and outbound digest
contain the LLM-written summary, source link, and metadata only. Raw article
bodies are transient summary input and are neither archived nor sent.

## Scheduling

Install a recurring poll every 30 minutes:

```sh
newswatcher schedule install
```

Choose another interval with minutes, `Nm`, or `Nh`, and inspect or remove the
job as needed:

```sh
newswatcher schedule install --every 2h
newswatcher schedule status
newswatcher schedule remove
```

Scheduling uses `crontab` on Linux and macOS and `schtasks` on Windows. On Windows
any interval under a day works (`--every 45`, `--every 5h`); on Linux and macOS cron
only fires intervals that divide evenly (15/20/30 min, 1/2/4/8/12 h, or daily) and
rejects the rest rather than mis-scheduling them. The scheduled process uses the same
configuration as an interactive poll, so make sure the LLM key is reachable (from
`credentials.json` or its environment variable) along with any settings not stored
in `config.toml`.

On Windows the task is registered under the installing user and runs in their
interactive session, so it does not fire while nobody is signed in — a locked screen is
fine, a machine sitting at the sign-in screen is not. It also inherits the Task Scheduler
default of not starting on battery power. Check it with
`schtasks /Query /TN newswatcher-poll`. On Linux and macOS the cron job has neither
restriction.

A poll takes a single-instance lock, so a scheduled poll and a manual one never run
at once — whichever starts second logs that a poll is already running and exits. The
lock uses `flock` on Linux and macOS and `msvcrt` on Windows.

## Use it from an AI coding agent

This repo ships a `poll` skill: ask in plain words ("run my newswatcher poll", "check the
news") and it runs one poll and relays what it found.

### Claude Code

In the Claude Code chat, add the marketplace and install:

```
/plugin marketplace add seokhoonj/newswatcher
/plugin install newswatcher@newswatcher
```

Then invoke it with `/newswatcher:poll`, or just ask in plain language. The skill calls the
`newswatcher` command, so install the package too (`pip install newswatcher`). See
`plugins/newswatcher/skills/poll/SKILL.md`.

### Codex

In your terminal, add the marketplace and install:

```
codex plugin marketplace add seokhoonj/newswatcher
codex plugin add newswatcher@newswatcher
```

The `poll` skill responds automatically to matching requests.

### By hand (symlink)

Symlink the skill into your skills directory and call it as `/poll`:

```sh
ln -s "$PWD/plugins/newswatcher/skills/poll" ~/.claude/skills/poll   # Claude Code -> /poll
ln -s "$PWD/plugins/newswatcher/skills/poll" ~/.codex/skills/poll    # Codex -> $newswatcher:poll
```

Claude Code picks it up immediately; Codex needs a restart to load it.
