# 해외 언론사 RSS 피드 목록 (영어권)

영어권 주요 해외 언론사를 카테고리별로 정리한 표. `RSS` 열의 ✅ 는 **실제 fetch로
검증된** 피드가 있다는 뜻이고, ❌ 는 검증 시점에 살아있는 공개 RSS를 확인하지 못했다는
뜻이다. ✅ 의 URL은 그대로 newswatch `add-source --kind rss` 에 넣을 수 있다. 피드는
영어이므로 토픽 키워드도 영어로 맞춘다.

- 검증 일자: 2026-09-01
- 검증 방법: 각 매체의 공개 RSS 후보 경로를 직접 요청해 feedparser로 파싱, 항목(entry)이
  실제로 채워지는 피드만 ✅ 로 채택. 여러 후보가 있으면 살아있는 것을 골랐다.
- `항목수` = 검증 시점에 피드가 반환한 기사 개수(살아있음의 신호, 갱신에 따라 달라짐).
- `범위`: **전체** = 사이트 전체/헤드라인 통합 피드 / **섹션** = 섹션 피드만 확인됨(URL은 대표 섹션).
- `본문`: **무료** = 기사 전문을 그대로 읽을 수 있음 / **유료** = 피드의 헤드라인·요약은
  무료지만 전문은 페이월·미터드(metered)라 로그인/결제 없이는 일부만 보임.

## 본문 유료가 요약에 미치는 영향 (읽고 등록할 것)

RSS **피드 자체는 전부 무료**다(공개 XML, 키 불필요). 다만 `본문=유료` 인 매체는
newswatch가 요약을 위해 기사 본문을 fetch할 때 페이월/티저만 잡혀 **요약이 얕아질 수
있다** — 이때 newswatch는 기사 전문 대신 피드가 준 짧은 요약으로 자동 대체(fallback)하므로
동작은 계속되지만 요약 품질은 헤드라인+블러브 수준이 된다. robots 정책이 본문을 막는
경우도 같은 방식으로 우아하게 대체된다. (Reuters·AP·Bloomberg Terminal 같은 유료 뉴스
API는 RSS가 아니며 여기 목록과 무관하다.)

## 통신사 / 글로벌

| 매체 | RSS | 피드 URL | 범위 | 항목수 | 본문 |
|------|:---:|----------|------|-------:|:----:|
| BBC News | ✅ | https://feeds.bbci.co.uk/news/world/rss.xml | 전체 | 38 | 무료 |
| The Guardian | ✅ | https://www.theguardian.com/world/rss | 전체 | 45 | 무료 |
| Al Jazeera | ✅ | https://www.aljazeera.com/xml/rss/all.xml | 전체 | 25 | 무료 |
| Euronews | ✅ | https://www.euronews.com/rss | 전체 | 50 | 무료 |
| Deutsche Welle | ✅ | https://rss.dw.com/xml/rss-en-all | 전체 | 135 | 무료 |
| France 24 | ✅ | https://www.france24.com/en/france/rss | 섹션 | 30 | 무료 |
| Reuters | ❌ | — | — | — | — |
| Associated Press | ❌ | — | — | — | — |

Reuters·AP 는 공개 RSS 제공을 중단했다(유료 뉴스 API로 전환). 비공식 서드파티 미러가
돌아다니지만 안정성·정당성을 보장할 수 없어 등재하지 않는다. 이 두 곳의 기사는 필요하면
newswatch `--kind crawl` 어댑터로 붙이거나 Google News 검색 피드로 우회할 수 있다.

## 미국 / 영국 신문·방송

| 매체 | RSS | 피드 URL | 범위 | 항목수 | 본문 |
|------|:---:|----------|------|-------:|:----:|
| The Independent | ✅ | https://www.independent.co.uk/news/world/rss | 전체 | 91 | 무료 |
| The New York Times | ✅ | https://rss.nytimes.com/services/xml/rss/nyt/World.xml | 섹션(World) | 58 | 유료 |
| CNN | ✅ | http://rss.cnn.com/rss/edition.rss | 전체 | 50 | 무료 |
| The Times of India | ✅ | https://timesofindia.indiatimes.com/rssfeedstopstories.cms | 전체 | 47 | 무료 |
| CBS News | ✅ | https://www.cbsnews.com/latest/rss/world | 섹션(World) | 30 | 무료 |
| ABC News | ✅ | https://abcnews.go.com/abcnews/topstories | 전체 | 25 | 무료 |
| The Washington Post | ✅ | https://feeds.washingtonpost.com/rss/world | 섹션(World) | 15 | 유료 |
| NPR | ✅ | https://feeds.npr.org/1001/rss.xml | 전체 | 10 | 무료 |
| Sky News | ✅ | https://feeds.skynews.com/feeds/rss/world.xml | 섹션(World) | 8 | 무료 |

## 경제 / 금융

| 매체 | RSS | 피드 URL | 범위 | 항목수 | 본문 |
|------|:---:|----------|------|-------:|:----:|
| The Economist | ✅ | https://www.economist.com/finance-and-economics/rss.xml | 섹션 | 300 | 유료 |
| Yahoo Finance | ✅ | https://finance.yahoo.com/news/rssindex | 전체 | 50 | 무료 |
| CNBC | ✅ | https://www.cnbc.com/id/100003114/device/rss/rss.html | 섹션 | 30 | 무료 |
| Forbes | ✅ | https://www.forbes.com/business/feed/ | 섹션 | 25 | 무료 |
| Bloomberg | ✅ | https://feeds.bloomberg.com/markets/news.rss | 섹션(Markets) | 20 | 유료 |
| Wall Street Journal | ✅ | https://feeds.a.dj.com/rss/RSSWorldNews.xml | 섹션(World) | 20 | 유료 |
| Business Insider | ✅ | https://www.businessinsider.com/rss | 전체 | 20 | 무료 |
| Financial Times | ✅ | https://www.ft.com/rss/home | 전체 | 10 | 유료 |
| MarketWatch | ✅ | http://feeds.marketwatch.com/marketwatch/topstories/ | 전체 | 10 | 무료 |
| Fortune | ✅ | https://fortune.com/feed/ | 전체 | 10 | 유료 |

## 기술 / IT

| 매체 | RSS | 피드 URL | 범위 | 항목수 | 본문 |
|------|:---:|----------|------|-------:|:----:|
| Wired | ✅ | https://www.wired.com/feed/rss | 전체 | 50 | 유료 |
| TechCrunch | ✅ | https://techcrunch.com/feed/ | 전체 | 20 | 무료 |
| Ars Technica | ✅ | https://feeds.arstechnica.com/arstechnica/index | 전체 | 20 | 무료 |
| Engadget | ✅ | https://www.engadget.com/rss.xml | 전체 | 20 | 무료 |
| Hacker News | ✅ | https://hnrss.org/frontpage | 전체 | 20 | 무료 |
| The Verge | ✅ | https://www.theverge.com/rss/index.xml | 전체 | 10 | 무료 |
| MIT Technology Review | ✅ | https://www.technologyreview.com/feed/ | 전체 | 10 | 유료 |
| ZDNet | ❌ | — | — | — | — |

## 과학

| 매체 | RSS | 피드 URL | 범위 | 항목수 | 본문 |
|------|:---:|----------|------|-------:|:----:|
| Nature | ✅ | https://www.nature.com/nature.rss | 전체 | 75 | 유료 |
| Scientific American | ✅ | https://www.scientificamerican.com/platform/syndication/rss/ | 전체 | 50 | 무료 |
| Science (AAAS) | ✅ | https://www.science.org/rss/news_current.xml | 전체 | 10 | 유료 |
| New Scientist | ❌ | — | — | — | — |

## 섹션 피드 넓히기

`범위`가 **섹션**인 매체는 다른 섹션 피드도 각각 소스로 등록해 커버리지를 넓힐 수 있다(패턴은 매체마다 다름):

- BBC: `https://feeds.bbci.co.uk/news/<world|business|technology|science_and_environment>/rss.xml`
- The Guardian: `https://www.theguardian.com/<world|business|technology|science>/rss`
- New York Times: `https://rss.nytimes.com/services/xml/rss/nyt/<World|Business|Technology|Science>.xml`
- CNBC: id 기반 섹션 피드(`.../id/<섹션ID>/device/rss/rss.html`)
- WSJ: `https://feeds.a.dj.com/rss/<RSSWorldNews|RSSMarketsMain|RSSWSJD>.xml`

## 등록 예시

```sh
newswatch add-topic markets --include stocks Fed "interest rate" earnings --exclude sports
newswatch add-source "BBC" https://feeds.bbci.co.uk/news/world/rss.xml --kind rss --topic markets
newswatch add-source "Reuters via crawl" https://www.reuters.com/world/ --kind crawl \
  --item article --title h3 --link a@href --topic markets
```
