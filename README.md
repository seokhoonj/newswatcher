# newswatch

newswatch watches RSS feeds and robots-permitted listing pages, matches new
articles against topics you define, summarizes the matches with an LLM, and
emails one topic-grouped digest.

## Install

newswatch requires Python 3.11 or newer.

```sh
pip install newswatch
```

## Quickstart

Define a topic, register an RSS source, provide a digest recipient and the API
key for the default Gemini LLM provider, then run one poll:

```sh
newswatch add-topic insurance --include insurance reinsurance --exclude sports
newswatch add-source industry-news https://example.com/feed.xml \
  --kind rss --topic insurance
export NEWSWATCH_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatch poll
```

Use `newswatch topics` and `newswatch sources` to inspect the registries. Run
`newswatch --help` or `newswatch <command> --help` for all commands and options.

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
name = "insurance"
includes = ["insurance", "reinsurance", "underwriting"]
excludes = ["sports"]

[[topic]]
name = "regulation"
includes = ["regulator", "solvency", "capital requirement"]
```

`sources.toml` contains RSS or crawl sources. `topics` selects the topic filters
applied to a source. Set `keep_all = true` for a source whose every article
should be retained without keyword filtering.

```toml
[[source]]
name = "industry-feed"
kind = "rss"
url = "https://example.com/feed.xml"
topics = ["insurance", "regulation"]

[[source]]
name = "regulator-news"
kind = "crawl"
url = "https://example.gov/news"
topics = ["regulation"]
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
`NEWSWATCH_DIGEST_TO` maps to `digest_to`. The article archive and run state use
the XDG data and state directories; `NEWSWATCH_DATA_DIR` and
`NEWSWATCH_STATE_DIR` can override them.

## Responsible collection

Every feed, listing-page, and article request is checked against the site's
robots policy before it is sent, and newswatch identifies itself with its user
agent. A disallowed URL is not fetched. The durable archive and outbound email
contain the LLM-written summary, source link, and metadata only. Raw article
bodies are transient summary input and are neither archived nor emailed.

## Scheduling

Install a recurring cron poll every 30 minutes:

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

Scheduling requires the `crontab` command. The scheduled process uses the same
configuration as an interactive poll, so make sure its environment provides the
LLM key and any settings not stored in `config.toml`.
