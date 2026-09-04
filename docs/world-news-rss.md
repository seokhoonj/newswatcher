# Overseas (English-language) news RSS feeds

Major English-language overseas outlets by category (general news + insurance/finance trade
press). In the **RSS** column, ✅ means a feed was **actually fetched and verified**, ❌ means
no live public RSS could be confirmed at verification time, and 🔒 means the feed exists but
Cloudflare returns 403 even to newswatcher's own user agent, so it cannot be polled. A ✅ URL
can go straight into `newswatcher add-source --kind rss`. The feeds are in English, so match
them with English topic keywords.

- Verified: 2026-09-01
- Method: each outlet's likely public RSS paths were requested directly and parsed with
  `feedparser`, and only feeds that actually returned entries were marked ✅ (the live one was
  chosen when several candidates existed). **The final check used newswatcher's own fetch (its
  identifying UA + the robots gate)** — the same request `add-source` makes — so Cloudflare
  sites that block a fake browser UA but let an honest bot through (Reinsurance News, Artemis,
  …) are judged correctly.
- **Items** — how many articles the feed returned at verification. A liveness signal only; it
  changes as the feed updates.
- **Scope** — **Full** = one feed for the whole site (or its headline roll-up). **Section** =
  only per-section feeds were found, and the URL is a representative section.
- **Body** — **Free** = the full article text is readable. **Paywalled** = the feed's headline
  and summary are free, but the body is behind a paywall or metered, so only part is visible
  without a login or payment.

## How a paywalled body affects the summary (read before adding)

The **RSS feeds themselves are all free** (public XML, no key). But for a `Body = Paywalled`
outlet, when newswatcher fetches the article body to summarize it, it may catch only the
paywall or a teaser, so **the summary can be shallow** — newswatcher then falls back to the
short summary the feed itself provides, so it keeps working but the quality drops to
headline-plus-blurb. A robots policy that blocks the body degrades the same way. (Paid news
APIs like Reuters, AP, or the Bloomberg Terminal are not RSS and are unrelated to this list.)

## Wire services / global

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| Al Jazeera | ✅ | https://www.aljazeera.com/xml/rss/all.xml | Full | 25 | Free |
| BBC News | ✅ | https://feeds.bbci.co.uk/news/world/rss.xml | Full | 38 | Free |
| Deutsche Welle | ✅ | https://rss.dw.com/xml/rss-en-all | Full | 135 | Free |
| Euronews | ✅ | https://www.euronews.com/rss | Full | 50 | Free |
| France 24 | ✅ | https://www.france24.com/en/france/rss | Section | 30 | Free |
| The Guardian | ✅ | https://www.theguardian.com/world/rss | Full | 45 | Free |
| Associated Press | ❌ | — | — | — | — |
| Reuters | ❌ | — | — | — | — |

Reuters and AP have discontinued their public RSS (they moved to paid news APIs). Unofficial
third-party mirrors circulate but cannot be vouched for on stability or legitimacy, so they
are not listed. If you need these two, attach them with newswatcher's `--kind crawl` adapter,
or route around them with a Google News search feed.

## US / UK press & broadcast

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| ABC News | ✅ | https://abcnews.go.com/abcnews/topstories | Full | 25 | Free |
| CBS News | ✅ | https://www.cbsnews.com/latest/rss/world | Section (World) | 30 | Free |
| CNN | ✅ | http://rss.cnn.com/rss/edition.rss | Full | 50 | Free |
| NPR | ✅ | https://feeds.npr.org/1001/rss.xml | Full | 10 | Free |
| Sky News | ✅ | https://feeds.skynews.com/feeds/rss/world.xml | Section (World) | 8 | Free |
| The Independent | ✅ | https://www.independent.co.uk/news/world/rss | Full | 91 | Free |
| The New York Times | ✅ | https://rss.nytimes.com/services/xml/rss/nyt/World.xml | Section (World) | 58 | Paywalled |
| The Times of India | ✅ | https://timesofindia.indiatimes.com/rssfeedstopstories.cms | Full | 47 | Free |
| The Washington Post | ✅ | https://feeds.washingtonpost.com/rss/world | Section (World) | 15 | Paywalled |

## Business / finance

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| Bloomberg | ✅ | https://feeds.bloomberg.com/markets/news.rss | Section (Markets) | 20 | Paywalled |
| Business Insider | ✅ | https://www.businessinsider.com/rss | Full | 20 | Free |
| CNBC | ✅ | https://www.cnbc.com/id/100003114/device/rss/rss.html | Section | 30 | Free |
| Financial Times | ✅ | https://www.ft.com/rss/home | Full | 10 | Paywalled |
| Forbes | ✅ | https://www.forbes.com/business/feed/ | Section | 25 | Free |
| Fortune | ✅ | https://fortune.com/feed/ | Full | 10 | Paywalled |
| MarketWatch | ✅ | http://feeds.marketwatch.com/marketwatch/topstories/ | Full | 10 | Free |
| The Economist | ✅ | https://www.economist.com/finance-and-economics/rss.xml | Section | 300 | Paywalled |
| Wall Street Journal | ✅ | https://feeds.a.dj.com/rss/RSSWorldNews.xml | Section (World) | 20 | Paywalled |
| Yahoo Finance | ✅ | https://finance.yahoo.com/news/rssindex | Full | 50 | Free |

## Insurance / reinsurance trade

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| Artemis (ILS·cat bond) | ✅ | https://www.artemis.bm/feed/ | Full | 10 | Free |
| Business Insurance | ✅ | https://www.businessinsurance.com/rss | Full | 20 | Paywalled |
| Carrier Management | ✅ | https://www.carriermanagement.com/feed/ | Full | 10 | Free |
| Commercial Risk | ✅ | https://www.commercialriskonline.com/feed/ | Full | 100 | Free |
| Coverager | ✅ | https://coverager.com/feed/ | Full | 10 | Free |
| Digital Insurance | ✅ | https://www.dig-in.com/feed?rss=true | Full | 10 | Paywalled |
| Insurance Business | ✅ | https://www.insurancebusinessmag.com/us/rss/ | Full | 129 | Free |
| Insurance Journal | ✅ | https://www.insurancejournal.com/feed/ | Full | 30 | Free |
| Reinsurance News | ✅ | https://www.reinsurancene.ws/feed/ | Full | 10 | Free |
| PropertyCasualty360 | 🔒 | https://www.propertycasualty360.com/feed/ | Full | — | Paywalled |
| Insurance Insider | ❌ | — | — | — | — |
| Intelligent Insurer | ❌ | — | — | — | — |
| The Insurer | ❌ | — | — | — | — |

For reinsurance, **Reinsurance News and Artemis are ✅** — drop them straight into
`add-source --kind rss`. Both sit behind Cloudflare and return 403 to a datacenter IP with a
fake browser UA, but they answer 200 to newswatcher's honest identifying UA
(`newswatcher (+https://github.com/seokhoonj/newswatcher)`) — not spoofing is what gets you
through. 🔒 PropertyCasualty360 returns 403 even to newswatcher's UA, so it cannot be polled.
Actuarial trade press (The Actuary, Actuarial Post, SOA) had no public RSS to confirm (mostly
member-only publishing or bot-blocked) — attach it with the `--kind crawl` adapter.

## Finance / fintech trade

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| American Banker | ✅ | https://www.americanbanker.com/feed?rss=true | Full | 10 | Paywalled |
| CoinDesk | ✅ | https://www.coindesk.com/arc/outboundfeeds/rss/ | Full | 25 | Free |
| Finextra | ✅ | https://www.finextra.com/rss/headlines.aspx | Full | 57 | Free |
| Investing.com | ✅ | https://www.investing.com/rss/news.rss | Full | 10 | Free |
| PYMNTS | ✅ | https://www.pymnts.com/feed/ | Full | 10 | Free |
| Seeking Alpha | ✅ | https://seekingalpha.com/feed.xml | Full | 30 | Paywalled |
| Institutional Investor | ❌ | — | — | — | — |
| Pensions & Investments | ❌ | — | — | — | — |
| The Banker | ❌ | — | — | — | — |

## Technology / IT

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| Ars Technica | ✅ | https://feeds.arstechnica.com/arstechnica/index | Full | 20 | Free |
| Engadget | ✅ | https://www.engadget.com/rss.xml | Full | 20 | Free |
| Hacker News | ✅ | https://hnrss.org/frontpage | Full | 20 | Free |
| MIT Technology Review | ✅ | https://www.technologyreview.com/feed/ | Full | 10 | Paywalled |
| TechCrunch | ✅ | https://techcrunch.com/feed/ | Full | 20 | Free |
| The Verge | ✅ | https://www.theverge.com/rss/index.xml | Full | 10 | Free |
| Wired | ✅ | https://www.wired.com/feed/rss | Full | 50 | Paywalled |
| ZDNet | ❌ | — | — | — | — |

## Science

| Outlet | RSS | Feed URL | Scope | Items | Body |
|--------|:---:|----------|-------|------:|:----:|
| Nature | ✅ | https://www.nature.com/nature.rss | Full | 75 | Paywalled |
| New Scientist | ✅ | https://www.newscientist.com/section/news/feed/ | Section (News) | 10 | Paywalled |
| Science (AAAS) | ✅ | https://www.science.org/rss/news_current.xml | Full | 10 | Paywalled |
| Scientific American | ✅ | https://www.scientificamerican.com/platform/syndication/rss/ | Full | 50 | Free |

## Widening coverage with section feeds

Even where a full-site feed exists, an outlet that also offers per-section feeds lets you
register the sections you care about as separate sources to widen coverage (the pattern
differs per outlet):

- BBC: `https://feeds.bbci.co.uk/news/<world|business|technology|science_and_environment>/rss.xml`
- The Guardian: `https://www.theguardian.com/<world|business|technology|science>/rss`
- New York Times: `https://rss.nytimes.com/services/xml/rss/nyt/<World|Business|Technology|Science>.xml`
- CNBC: id-based section feeds (`.../id/<sectionID>/device/rss/rss.html`)
- WSJ: `https://feeds.a.dj.com/rss/<RSSWorldNews|RSSMarketsMain|RSSWSJD>.xml`

## Registration examples

```sh
newswatcher add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
newswatcher add-source "BBC" https://feeds.bbci.co.uk/news/world/rss.xml --kind rss --topic markets

newswatcher add-topic insurance --include reinsurance underwriting "catastrophe bond" solvency
newswatcher add-source "Insurance Journal" https://www.insurancejournal.com/feed/ --kind rss --topic insurance
newswatcher add-source "Insurance Business" https://www.insurancebusinessmag.com/us/rss/ --kind rss --topic insurance
```
