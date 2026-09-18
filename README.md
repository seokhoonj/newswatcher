# newswatcher

[![check](https://github.com/seokhoonj/newswatcher/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/newswatcher/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/newswatcher)](https://pypi.org/project/newswatcher/)
[![Python](https://img.shields.io/pypi/pyversions/newswatcher)](https://pypi.org/project/newswatcher/)
[![License](https://img.shields.io/pypi/l/newswatcher)](https://github.com/seokhoonj/newswatcher/blob/main/LICENSE)

**English** | [한국어](README.ko.md)

newswatcher watches RSS feeds and robots-permitted listing pages, matches new
articles against topics you define, summarizes the matches with an LLM, and
sends one topic-grouped digest by email, chat, or both. Delivery is optional — the
core collects, summarizes, and archives on its own; email and chat are opt-in add-ons
(`newswatcher[email]` / `newswatcher[chat]`). Several outlets covering the same story
collapse into a single entry. The topics are yours to define, so
the same tool tracks a stock ticker, a technology, a policy beat, or any subject
a feed covers.

## 1. Install

newswatcher requires Python 3.11 or newer. The core — collect, summarize, archive — installs on
its own; delivery is opt-in, so add the channel you want:

```sh
pip install newswatcher            # core: collect, summarize, archive (read with `articles`)
pip install "newswatcher[email]"   # + email digests, via mailmail
pip install "newswatcher[chat]"    # + chat digests, via pushpush
pip install "newswatcher[all]"     # + both
```

The Quickstart below needs only the core `newswatcher` — email and chat come later (Delivery).

## 2. Quickstart

These are terminal commands (a shell — Terminal, PowerShell, or Command Prompt — not the
Python prompt). First get a free Gemini API key from
[Google AI Studio](https://aistudio.google.com/apikey) (sign in with Google, click **Create
API key**, copy it), then store it — you are prompted, and the key is not echoed:

```sh
newswatcher set-key gemini
```

Define a topic, register an RSS source, run one pass, and read the summaries — no email setup
needed to get a first result:

```sh
newswatcher add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
newswatcher add-source korea-herald "https://www.koreaherald.com/rss/newsAll" --kind rss --topic markets
newswatcher poll --no-mail
newswatcher articles
```

A topic matches on the feed's own language, so pair the keywords with the feed: English
keywords for an English feed, Korean keywords for a Korean feed. `newswatcher topics` and
`newswatcher sources` show what you registered.

To have the digest **emailed** or sent to **chat** instead of read with `articles`, install the
delivery extra and configure the channel once — see [Delivery](#4-delivery).

## 3. Commands

Run `newswatcher --help` or `newswatcher <command> --help` for every option;
`newswatcher --version` prints the version.

| Command | What it does |
|---------|--------------|
| `add-topic <name> [--include WORD...] [--exclude WORD...]` | Define a topic filter: a name, `--include` keywords (an article matches when it has any one of them), and optional `--exclude` keywords (any one rejects it). Empty includes match every article. |
| `topics` | List the defined topics with their include / exclude keywords. |
| `add-source <name> <url> [--kind rss\|crawl] [--topic NAME]... [--keep-all]` | Register a source — an RSS feed (`--kind rss`) or a robots-permitted crawl page (`--kind crawl`) — and the `--topic`s to test it against. A crawl source also needs selectors: `--item --title --link` (required), `--date --body-selector` (optional). `--keep-all` keeps every article from the source without keyword filtering (for a trade feed that is wholly on-topic). |
| `sources` | List the registered sources with their kind, URL, and topics. |
| `set-key <provider>` | Store an LLM provider's API key with thinchat, prompted without echo (in thinchat's own credential store). The provider is `gemini`, `openai`, or `claude`; the key is also read from the matching `*_API_KEY` environment variable, which takes precedence. |
| `setup [--provider P]` | Fill in the missing secrets for every channel in one guided pass — the LLM key with thinchat, each email password with mailmail, each chat token with pushpush — prompting without echo and printing where each landed. Skips what is already set, and points you at the tool to configure a channel that has no account or route yet. |
| `doctor [--provider P]` | Show where each secret and config file lives and whether it is set, without printing any secret. Exits non-zero when a configured channel is missing its secret or its store is unreadable, so a scheduled run can gate on a complete setup. |
| `recent <url> [--limit N]` | Fetch and print a feed's latest items (title + link) without storing or summarizing — a quick check of a URL before you register it. `--limit N` caps how many. |
| `poll` | Run one pass: fetch every source, keep the new articles that match a topic, summarize them, archive them, and send the digest. `--to` / `--push` set destinations; `--no-mail` collects without sending; `--no-store` skips archiving; `--no-heal` skips selector repair; `--provider` / `--model` choose the LLM. |
| `watch [--every N]` | Run `poll` repeatedly in the foreground, every `--every` minutes (default 30), until you stop it. Takes all of `poll`'s options. |
| `articles [--topic NAME] [--since DATE] [--until DATE]` | List archived articles (title, our summary, link), optionally narrowed to a topic and a half-open `[since, until)` date range. |
| `heal [--dry-run] [--provider P] [--model M]` | Check crawl sources whose selectors stopped matching and repair them with an LLM, validated against the live page. `--dry-run` reports the proposed fix without writing it. |
| `schedule install\|status\|remove [--every N]` | Install, show, or remove the recurring poll in the OS scheduler (cron on Linux/macOS, schtasks on Windows). `--every N` sets the interval. |

## 4. Delivery

The digest is sent by email, to a chat channel, or both — set one or both destinations.
Each channel is an opt-in extra (`newswatcher[email]` / `newswatcher[chat]`); its companion
package keeps its own credentials, so newswatcher never stores your email password or bot token.
Without either extra, newswatcher still collects, summarizes, and archives — read the archive with
`newswatcher articles`.

- Email goes through the mailmail package (`newswatcher[email]`). Set up an account (or an
  address-book alias) once with mailmail's own CLI (`mailmail --help`); then `--to ADDRESS`, or the
  `NEWSWATCHER_DIGEST_TO` setting, names that alias or a plain address.
- Chat goes through the pushpush package (`newswatcher[chat]`). Configure a route (a bot plus its
  destination — Telegram, Slack, or Discord) once with pushpush's own CLI (`pushpush --help`); then
  `--push ROUTE`, or the `NEWSWATCHER_DIGEST_PUSH` setting, names that route. The digest is sent as
  one markdown message.

So newswatcher holds no secret of its own: the LLM key lives with thinchat, the email password
with mailmail, the chat token with pushpush — each in its own store, exactly as when the tool is
used on its own. Configure them all in one guided pass with `newswatcher setup`, and see the full
map — what is set and where it lives — with `newswatcher doctor`.

## 5. News feeds

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

## 6. Configuration files

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

## 7. Provider keys and model

A **provider** is the LLM service that writes the summaries. newswatcher supports four; pass the
name in the left column to `--provider` or `set-key`:

| Provider | Key (environment variable) | Where to get a key |
|----------|----------------------------|--------------------|
| `gemini` (default) | `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) — free tier |
| `openai` | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| `claude` | `CLAUDE_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `ollama` | — (runs locally) | no key needed |

The provider key is a secret, and it lives with thinchat — the library newswatcher
summarizes through — not with newswatcher. Store it once with `setup` (which configures
email and chat in the same pass) or with `set-key` for the key alone; both prompt without
echoing and write to thinchat's own credential store:

```sh
newswatcher setup            # the LLM key, plus email and chat, in one pass
newswatcher set-key gemini   # just the LLM key
```

Each key is also read from its environment variable (the table above), which takes precedence,
so a one-off run can supply a key without storing anything.

newswatcher summarizes with Gemini's free tier by default. Choose another provider,
and optionally a specific model, with `--provider` / `--model`, or persistently
with the `NEWSWATCHER_LLM_PROVIDER` / `NEWSWATCHER_LLM_MODEL` settings (`llm_provider`
and `llm_model` in `config.toml`):

```sh
newswatcher poll --provider claude --model claude-sonnet-5
export NEWSWATCHER_LLM_PROVIDER=openai
```

## 8. Responsible collection

Every feed, listing-page, and article request is checked against the site's
robots policy before it is sent, and newswatcher identifies itself with its user
agent. A disallowed URL is not fetched. The durable archive and outbound digest
contain the LLM-written summary, source link, and metadata only. Raw article
bodies are transient summary input and are neither archived nor sent.

## 9. Scheduling

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
thinchat's store or its environment variable) along with any settings not stored
in `config.toml`. `newswatcher doctor` confirms it before you schedule.

On Windows the task is registered under the installing user and runs in their
interactive session, so it does not fire while nobody is signed in — a locked screen is
fine, a machine sitting at the sign-in screen is not. It also inherits the Task Scheduler
default of not starting on battery power. Check it with
`schtasks /Query /TN newswatcher-poll`. On Linux and macOS the cron job has neither
restriction.

A poll takes a single-instance lock, so a scheduled poll and a manual one never run
at once — whichever starts second logs that a poll is already running and exits. The
lock uses `flock` on Linux and macOS and `msvcrt` on Windows.

## 10. Use it from an AI coding agent

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

## 11. License

[MIT](LICENSE)
