# 국내 언론사 RSS 피드 목록

국내 언론사를 분야별로 최대한 모은 표다. 한 행이 언론사 하나이고, **RSS** 열의 표시가 그
언론사의 공개 RSS 피드 상태를 뜻한다.

- **✅** = 직접 받아서 확인한 **살아있는 RSS 피드가 있다.** 이 URL은 그대로
  `newswatcher add-source --kind rss` 에 넣으면 된다.
- **❌** = 검증 시점(2026-08-20)에 **살아있는 공개 RSS를 찾지 못했다.** "이 언론사는 RSS가
  없다"는 뜻이 아니다 — 이유는 맨 아래 "❌ 표시에 대해" 참고.

각 열의 뜻:

- **피드 URL** — ✅ 인 곳의 실제 피드 주소.
- **범위** — 이 피드가 사이트 전체를 담는지 한 섹션만 담는지.
  - **전체** = 그 사이트의 모든 기사를 모은 통합 피드 하나. 이거 하나만 등록하면 다 받는다.
  - **섹션** = 정치·경제 같은 섹션별 피드만 있는 경우로, 표에는 그중 대표 섹션 하나만 적었다.
    그 URL만 등록하면 그 섹션 기사만 들어온다 (넓히는 법은 "섹션별 피드 다중 등록" 참고).
- **항목수** — 검증 때 그 피드가 돌려준 기사 개수. 피드가 살아있다는 신호일 뿐, 갱신에 따라 바뀐다.

검증 방법: 각 언론사 홈페이지와 RSS 인덱스에서 피드 링크를 자동으로 찾고, 흔한 피드 경로
후보들을 직접 요청해 `feedparser` 로 파싱했다. **기사(entry)가 실제로 채워지는 피드만 ✅** 로
채택했으며, 한 사이트에서 섹션 피드가 여러 개 잡히면 전체 통합 피드를 우선했다.

## 종합일간지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 경향신문 | ✅ | https://www.khan.co.kr/rss/rssdata/total_news.xml | 전체 | 50 |
| 국민일보 | ✅ | https://www.kmib.co.kr/rss/data/kmibRssAll.xml | 전체 | 30 |
| 동아일보 | ✅ | https://rss.donga.com/total.xml | 전체 | 50 |
| 서울신문 | ✅ | https://www.seoul.co.kr/xml/rss/google_plan.xml | 전체 | 40 |
| 세계일보 | ✅ | http://www.segye.com/Articles/RSSList/segye_recent.xml | 전체 | 20 |
| 조선일보 | ✅ | https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml | 전체 | 100 |
| 한겨레 | ✅ | https://www.hani.co.kr/rss/ | 전체 | 30 |
| 내일신문 | ❌ | — | — | — |
| 문화일보 | ❌ | — | — | — |
| 중앙일보 | ❌ | — | — | — |
| 한국일보 | ❌ | — | — | — |

## 경제지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| EBN | ✅ | https://cdn.ebn.co.kr/rss/gns_allArticle.xml | 전체 | 50 |
| 매일경제 | ✅ | https://www.mk.co.kr/rss/30000001/ | 섹션(헤드라인) | 50 |
| 머니투데이 | ✅ | http://rss.mt.co.kr/mt_news.xml | 전체 | 100 |
| 메트로 | ✅ | https://www.metroseoul.co.kr/news/rss | 전체 | 50 |
| 브릿지경제 | ✅ | https://www.viva100.com/rssAll.xml | 전체 | 50 |
| 서울경제 | ✅ | https://www.sedaily.com/rss/newsall | 전체 | 50 |
| 서울파이낸스 | ✅ | https://cdn.seoulfn.com/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 아시아경제 | ✅ | https://view.asiae.co.kr/rss/all.htm | 전체 | 100 |
| 아주경제 | ✅ | https://www.ajunews.com/rss/sokbo.xml | 전체 | 802 |
| 이데일리 | ✅ | http://rss.edaily.co.kr/edaily_news.xml | 전체 | 50 |
| 이투데이 | ✅ | https://rss.etoday.co.kr/eto/etoday_news_all.xml | 전체 | 231 |
| 조선비즈 | ✅ | https://biz.chosun.com/arc/outboundfeeds/rss/?outputType=xml | 전체 | 100 |
| 조세일보 | ✅ | https://www.joseilbo.com/Contents/rss/rss_total.php | 전체 | 20 |
| 파이낸셜뉴스 | ✅ | https://www.fnnews.com/rss/r20/fn_realnews_all.xml | 전체 | 372 |
| 프라임경제 | ✅ | https://www.newsprime.co.kr/data/rss/news.xml | 전체 | 25 |
| 한국경제 | ✅ | https://www.hankyung.com/feed/all-news | 전체 | 50 |
| 헤럴드경제 | ✅ | https://biz.heraldcorp.com/rss/google/newsAll | 전체 | 300 |
| 글로벌이코노믹 | ❌ | — | — | — |
| 뉴스핌 | ❌ | — | — | — |
| 데일리안 | ❌ | — | — | — |
| 머니S | ❌ | — | — | — |
| 비즈워치 | ❌ | — | — | — |
| 인베스트조선 | ❌ | — | — | — |

## IT / 과학 / 전문

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| IT동아 | ✅ | https://it.donga.com/feeds/rss/ | 전체 | 100 |
| 바이라인네트워크 | ✅ | https://byline.network/feed/ | 전체 | 20 |
| 보안뉴스 | ✅ | https://www.boannews.com/media/news_rss.xml | 전체 | 10 |
| 블로터 | ✅ | https://cdn.bloter.net/rss/gns_allArticle.xml | 전체 | 50 |
| 아이뉴스24 | ✅ | https://www.inews24.com/rss/news_all.xml | 전체 | 100 |
| 전자신문 | ✅ | https://rss.etnews.com/Section901.xml | 섹션 | 30 |
| 지디넷코리아 | ✅ | https://feeds.feedburner.com/zdkorea | 전체 | 30 |
| 코메디닷컴 | ✅ | https://kormedi.com/feed/ | 전체 | 10 |
| 테크M | ✅ | https://www.techm.kr/rss/allArticle.xml | 전체 | 50 |
| 동아사이언스 | ❌ | — | — | — |
| 디지털데일리 | ❌ | — | — | — |
| 디지털타임스 | ❌ | — | — | — |

## 통신사

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 뉴시스 | ✅ | https://www.newsis.com/RSS/sokbo.xml | 섹션(속보) | 100 |
| 연합뉴스 | ✅ | https://www.yna.co.kr/rss/news.xml | 전체 | 120 |
| 뉴스1 | ❌ | — | — | — |

## 방송

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| JTBC | ✅ | https://fs.jtbc.co.kr/RSS/newsflash.xml | 섹션(속보) | 20 |
| MBN | ✅ | https://www.mbn.co.kr/rss/politics/ | 섹션 | 30 |
| SBS | ✅ | https://news.sbs.co.kr/news/newsflashRssFeed.do | 섹션(속보) | 101 |
| TV조선 | ✅ | https://news.tvchosun.com/site/data/rss/rss.xml | 전체 | 50 |
| 연합뉴스TV | ✅ | https://www.yonhapnewstv.co.kr/browse/feed/ | 전체 | 11 |
| KBS | ❌ | — | — | — |
| MBC | ❌ | — | — | — |
| YTN | ❌ | — | — | — |
| 채널A | ❌ | — | — | — |

## 인터넷 / 시사

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 노컷뉴스 | ✅ | https://rss.nocutnews.co.kr/news/news.xml | 전체 | 50 |
| 데일리NK | ✅ | https://www.dailynk.com/feed/ | 전체 | 10 |
| 미디어오늘 | ✅ | http://www.mediatoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 시사IN | ✅ | https://www.sisain.co.kr/rss/allArticle.xml | 전체 | 50 |
| 시사저널 | ✅ | https://www.sisajournal.com/rss/allArticle.xml | 전체 | 50 |
| 오마이뉴스 | ✅ | http://rss.ohmynews.com/rss/ohmynews.xml | 전체 | 20 |
| 주간경향 | ✅ | https://weekly.khan.co.kr/rss/rssdata/world_news.xml | 섹션 | 50 |
| 폴리뉴스 | ✅ | https://www.polinews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 프레시안 | ✅ | https://www.pressian.com/api/v3/site/rss/news | 전체 | 25 |
| 한겨레21 | ✅ | https://h21.hani.co.kr/rss/ | 전체 | 30 |
| 뉴데일리 | ❌ | — | — | — |
| 뉴스타파 | ❌ | — | — | — |
| 미디어펜 | ❌ | — | — | — |
| 민중의소리 | ❌ | — | — | — |

## 보험 / 금융 전문지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 금융소비자뉴스 | ✅ | https://www.newsfc.co.kr/rss/allArticle.xml | 전체 | 50 |
| 대한금융신문 | ✅ | https://www.kbanker.co.kr/rss/allArticle.xml | 전체 | 50 |
| 보험매일 | ✅ | https://www.fins.co.kr/rss/allArticle.xml | 전체 | 50 |
| 보험저널 | ✅ | https://www.insjournal.co.kr/rss/allArticle.xml | 전체 | 50 |
| 파이낸셜투데이 | ✅ | https://www.ftoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 한국보험신문 | ✅ | https://www.insnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 더벨 | ❌ | — | — | — |
| 보험소비자신문 | ❌ | — | — | — |
| 인슈넷 | ❌ | — | — | — |
| 팍스넷뉴스 | ❌ | — | — | — |
| 한국금융신문 | ❌ | — | — | — |

## 의약 / 바이오

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 라포르시안 | ✅ | https://www.rapportian.com/rss/allArticle.xml | 전체 | 50 |
| 의협신문 | ✅ | https://www.doctorsnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 청년의사 | ✅ | https://www.docdocdoc.co.kr/rss/allArticle.xml | 전체 | 50 |
| 팜뉴스 | ✅ | https://www.pharmnews.com/rss/allArticle.xml | 전체 | 50 |
| 히트뉴스 | ✅ | https://www.hitnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 데일리팜 | ❌ | — | — | — |
| 메디게이트뉴스 | ❌ | — | — | — |
| 메디칼타임즈 | ❌ | — | — | — |
| 약업신문 | ❌ | — | — | — |

## 건설 / 부동산 / 에너지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 그린포스트코리아 | ✅ | https://www.greenpostkorea.co.kr/rss/allArticle.xml | 전체 | 50 |
| 대한전문건설신문 | ✅ | https://www.koscaj.com/rss/allArticle.xml | 전체 | 50 |
| 이투뉴스 | ✅ | https://www.e2news.com/rss/allArticle.xml | 전체 | 50 |
| 투데이에너지 | ✅ | https://www.todayenergy.kr/rss/allArticle.xml | 전체 | 50 |
| 하우징헤럴드 | ✅ | https://www.housingherald.co.kr/rss/allArticle.xml | 전체 | 50 |
| 건설경제 | ❌ | — | — | — |
| 에너지경제 | ❌ | — | — | — |

## 자동차 / 산업

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 모터그래프 | ✅ | https://www.motorgraph.com/rss/allArticle.xml | 전체 | 50 |
| 오토헤럴드 | ✅ | https://www.autoherald.co.kr/rss/allArticle.xml | 전체 | 50 |
| 오토타임즈 | ❌ | — | — | — |

## 교육 / 법률 / 노동

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 매일노동뉴스 | ✅ | https://www.labortoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 법률신문 | ✅ | https://cdn.lawtimes.co.kr/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 베리타스알파 | ✅ | https://www.veritas-a.com/rss/allArticle.xml | 전체 | 50 |
| 한국교육신문 | ✅ | https://www.hangyo.com/data/rss/news.xml | 전체 | 25 |

## 농업 / 환경

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 농수축산신문 | ✅ | https://www.aflnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 한국농정신문 | ✅ | https://www.ikpnews.net/rss/allArticle.xml | 전체 | 50 |
| 농민신문 | ❌ | — | — | — |

## 스포츠 / 연예

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| OSEN | ✅ | https://rss.mt.co.kr/osen_news.xml | 전체 | 49 |
| 스포츠조선 | ✅ | https://www.sportschosun.com/rss/index_all.htm | 전체 | 100 |
| 일간스포츠 | ✅ | https://isplus.com/rss | 전체 | 100 |
| 텐아시아 | ✅ | https://www.tenasia.co.kr/rss/music/ | 섹션 | 50 |
| 뉴스엔 | ❌ | — | — | — |
| 마이데일리 | ❌ | — | — | — |
| 스타뉴스 | ❌ | — | — | — |
| 스포츠동아 | ❌ | — | — | — |
| 스포츠서울 | ❌ | — | — | — |

## 지역지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 강원도민일보 | ✅ | https://www.kado.net/rss/allArticle.xml | 전체 | 50 |
| 경남도민일보 | ✅ | https://www.idomin.com/rss/allArticle.xml | 전체 | 50 |
| 대전일보 | ✅ | https://www.daejonilbo.com/rss/allArticle.xml | 전체 | 50 |
| 인천일보 | ✅ | https://www.incheonilbo.com/rss/allArticle.xml | 전체 | 50 |
| 전남일보 | ✅ | https://cdn.jnilbo.com/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 전북일보 | ✅ | https://www.jjan.kr/news/rssAll | 전체 | 50 |
| 제주일보 | ✅ | https://www.jejunews.com/rss/allArticle.xml | 전체 | 50 |
| 충청투데이 | ✅ | https://www.cctoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 한라일보 | ✅ | https://www.ihalla.com/rss.php?section=73 | 섹션 | 30 |
| 강원일보 | ❌ | — | — | — |
| 경기일보 | ❌ | — | — | — |
| 경남신문 | ❌ | — | — | — |
| 광주일보 | ❌ | — | — | — |
| 국제신문 | ❌ | — | — | — |
| 매일신문 | ❌ | — | — | — |
| 무등일보 | ❌ | — | — | — |
| 부산일보 | ❌ | — | — | — |
| 영남일보 | ❌ | — | — | — |
| 중도일보 | ❌ | — | — | — |

## 영자지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| The Korea Herald | ✅ | https://www.koreaherald.com/rss/newsAll | 전체 | 50 |
| The Korea Times | ✅ | https://feed.koreatimes.co.kr/k/allnews.xml | 전체 | 65 |
| Korea JoongAng Daily | ❌ | — | — | — |

## 해외 (재)보험 전문지

| 매체 | RSS | 피드 URL | 범위 | 항목수 |
|------|:---:|----------|------|-------:|
| Reinsurance News | ✅ | https://www.reinsurancene.ws/feed/ | 전체 | 10 |

## 섹션별 피드 다중 등록 — 범위가 "섹션"인 곳

대부분의 사이트는 **모든 기사를 한데 모은 "전체" 피드**를 하나 준다. 그거 하나만 등록하면
그 언론사 기사를 다 받는다.

그런데 일부 사이트는 전체 피드가 없고 **섹션별(정치·경제·사회…) 피드만** 준다. 이런
곳(매일경제, 전자신문, SBS, MBN, 뉴시스, 주간경향, 텐아시아, 한라일보)은 표에 **대표 섹션
하나의 피드만** 적혀 있어서, 그 URL만 등록하면 **그 섹션 기사만** 들어온다.

더 넓게 받고 싶으면 원하는 섹션들을 **각각 별도 소스로 등록**하면 된다. 예를 들어 매일경제
헤드라인과 경제 섹션을 다 받으려면 두 URL을 각각 `add-source` 로 넣는다. 섹션 URL 패턴은
사이트마다 다르다:

- 매일경제: `.../rss/<섹션코드>/` — 30000001(헤드라인), 40300001(경제) 등 섹션코드만 치환
- 전자신문: `https://rss.etnews.com/Section<번호>.xml`
- 서울경제: `https://www.sedaily.com/rss/<economy|finance|politics|society|...>` (전체는 `newsall`)
- 노컷뉴스: `https://rss.nocutnews.co.kr/category/<politics|economy|society|world|...>.xml`
- MBN: `https://www.mbn.co.kr/rss/<politics|economy|society|...>/`

## ❌ 표시에 대해

❌ 는 "이 언론사가 영원히 RSS가 없다"가 아니라, **2026-08-20 검증 시점에 흔히 쓰이던
피드 경로들에서 살아있는 공개 RSS를 확인하지 못했다**는 뜻이다. 원인은 대체로 다음 넷이다:

1. 과거 피드 URL이 404 또는 HTML 안내페이지로 바뀜
2. 피드 전용 호스트의 DNS 소멸
3. 홈페이지가 JS 렌더링 SPA라 피드 링크를 정적으로 노출하지 않음
4. RSS 제공 중단

특히 3번에 걸린 곳(중앙일보, 한국일보, KBS, MBC, YTN, 대형 지역지 상당수)은 실제로는 RSS가
있어도 이 자동 검증으로는 못 잡은 것일 수 있다. 정확한 피드 경로가 확인되면 해당 행을 ✅ 로
갱신하면 된다. RSS가 정말 없는 곳은 newswatcher의 `--kind crawl`(CSS 셀렉터 크롤) 어댑터로
붙일 수 있다.

## 등록 예시

```sh
newswatcher add-source "연합뉴스" https://www.yna.co.kr/rss/news.xml --kind rss
newswatcher add-source "조선일보" "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml" --kind rss
newswatcher add-source "한국보험신문" https://www.insnews.co.kr/rss/allArticle.xml --kind rss --topic insurance
```
