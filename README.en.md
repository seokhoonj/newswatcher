# newswatch

[한국어](README.md) | **English**

newswatch watches RSS feeds and robots-permitted listing pages, matches new
articles against topics you define, summarizes the matches with an LLM, and
sends one topic-grouped digest by email, chat, or both. Several outlets covering
the same story collapse into a single entry. The topics are yours to define, so
the same tool tracks a stock ticker, a technology, a policy beat, or any subject
a feed covers.

## Install

newswatch requires Python 3.11 or newer.

```sh
pip install newswatch
```

## Quickstart

Define a topic, register an RSS source, provide a digest recipient and the API
key for the default Gemini LLM provider, then run one poll:

```sh
newswatch add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
newswatch add-source korea-herald https://www.koreaherald.com/rss/newsAll \
  --kind rss --topic markets
export NEWSWATCH_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatch poll
```

A topic matches on the feed's own language, so pair the keywords with the feed:
English keywords for an English feed, Korean keywords for a Korean feed.

Use `newswatch topics` and `newswatch sources` to inspect the registries. Run
`newswatch --help` or `newswatch <command> --help` for all commands and options.

## Commands

Run `newswatch --help` or `newswatch <command> --help` for every option;
`newswatch --version` prints the version.

- `add-topic <name> [--include WORD...] [--exclude WORD...]` / `topics` — define and list topic filters.
- `add-source <name> <url> [--kind rss|crawl] [--topic NAME]... [--keep-all]` / `sources` — register and list sources. A crawl source also takes selectors: `--item --title --link` (required) and `--date --body-selector` (optional). `--keep-all` retains every article without keyword filtering.
- `recent <url> [--limit N]` — preview a feed's latest items without storing, to check it before adding.
- `poll` / `watch [--every N]` — collect → summarize → send once, or repeat on an interval in the foreground. Both accept `--to ADDRESS` (email recipient), `--push ROUTE` (a pushpush chat route), `--no-mail`, `--no-store`, `--no-heal`, and the LLM `--provider` / `--model` flags.
- `articles [--topic NAME] [--since DATE] [--until DATE]` — list archived articles.
- `heal [--dry-run] [--provider P] [--model M]` — check and repair crawl selectors that stopped matching.
- `schedule install|status|remove [--every N]` — register the recurring poll with the OS
  scheduler.

## Delivery

The digest is sent by email, to a chat channel, or both -- set one or both destinations.

- Email goes through mailmail: `--to ADDRESS` or the `NEWSWATCH_DIGEST_TO` setting (a
  mailmail address or address-book alias).
- Chat goes through pushpush: `--push ROUTE` or the `NEWSWATCH_DIGEST_PUSH` setting,
  naming a route you configured in pushpush (Telegram, Slack, or Discord). The digest is
  sent as one markdown message.

Both packages are installed with newswatch; configure a pushpush route with pushpush's
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

## Configuration files

newswatch stores hand-edited configuration under
`$XDG_CONFIG_HOME/newswatch`, or `~/.config/newswatch` when
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
`NEWSWATCH_DIGEST_TO` maps to `digest_to`, and `NEWSWATCH_DIGEST_PUSH` to `digest_push`.
The article archive and run state use
the XDG data and state directories; `NEWSWATCH_DATA_DIR` and
`NEWSWATCH_STATE_DIR` can override them.

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

newswatch summarizes with Gemini's free tier by default. Choose another provider,
and optionally a specific model, with `--provider` / `--model`, or persistently
with the `NEWSWATCH_LLM_PROVIDER` / `NEWSWATCH_LLM_MODEL` settings (`llm_provider`
and `llm_model` in `config.toml`):

```sh
newswatch poll --provider claude --model claude-sonnet-5
export NEWSWATCH_LLM_PROVIDER=openai
```

## Responsible collection

Every feed, listing-page, and article request is checked against the site's
robots policy before it is sent, and newswatch identifies itself with its user
agent. A disallowed URL is not fetched. The durable archive and outbound email
contain the LLM-written summary, source link, and metadata only. Raw article
bodies are transient summary input and are neither archived nor emailed.

## Scheduling

Install a recurring poll every 30 minutes:

```sh
newswatch schedule install
```

Choose another interval with minutes, `Nm`, or `Nh`, and inspect or remove the
job as needed:

```sh
newswatch schedule install --every 2h
newswatch schedule status
newswatch schedule remove
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
`schtasks /Query /TN newswatch-poll`. On Linux and macOS the cron job has neither
restriction.

A poll takes a single-instance lock, so a scheduled poll and a manual one never run
at once — whichever starts second logs that a poll is already running and exits. The
lock uses `flock` on Linux and macOS and `msvcrt` on Windows.
