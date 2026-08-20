# 국내 언론사 RSS 피드 목록

국내 언론사를 카테고리별로 최대한 망라한 표. `RSS` 열의 ✅ 는 **실제 fetch로 검증된**
피드가 있다는 뜻이고, ❌ 는 검증 시점에 살아있는 공개 RSS를 확인하지 못했다는 뜻이다.
✅ 의 URL은 그대로 newswatch `add-source --kind rss` 에 넣을 수 있다.

- 검증 일자: 2026-08-20
- 검증 방법: 각 언론사의 홈페이지 / RSS 인덱스 페이지에서 피드 링크를 자동 탐색하고,
  흔한 피드 경로 후보를 직접 요청해 feedparser로 파싱, 항목(entry)이 실제로 채워지는
  피드만 ✅ 로 채택. 여러 섹션 피드가 잡히면 전체(all/전체) 피드를 우선했다.
- ❌ = 후보 경로들이 404 / HTML 안내페이지 / DNS 소멸로 죽었거나, 홈페이지가 JS 렌더링
  SPA라 피드 링크를 정적으로 노출하지 않아 이번 자동 검증으로는 확인하지 못함(실제로
  RSS가 없다는 뜻은 아님. 경로가 확인되면 재검증해 ✅ 로 올리면 된다).
- `항목수` = 검증 시점에 피드가 반환한 기사 개수(살아있음의 신호, 갱신에 따라 달라짐).
- `범위`: **전체** = 사이트 전체 통합 피드 / **섹션** = 섹션별 피드만 제공(URL은 대표 섹션).

## 종합일간지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 조선일보 | ✅ | https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml | 전체 | 100 |
| 동아일보 | ✅ | https://rss.donga.com/total.xml | 전체 | 50 |
| 경향신문 | ✅ | https://www.khan.co.kr/rss/rssdata/total_news.xml | 전체 | 50 |
| 서울신문 | ✅ | https://www.seoul.co.kr/xml/rss/google_plan.xml | 전체 | 40 |
| 한겨레 | ✅ | https://www.hani.co.kr/rss/ | 전체 | 30 |
| 국민일보 | ✅ | https://www.kmib.co.kr/rss/data/kmibRssAll.xml | 전체 | 30 |
| 세계일보 | ✅ | http://www.segye.com/Articles/RSSList/segye_recent.xml | 전체 | 20 |
| 중앙일보 | ❌ | — | — | — |
| 한국일보 | ❌ | — | — | — |
| 문화일보 | ❌ | — | — | — |
| 내일신문 | ❌ | — | — | — |

## 경제지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 아주경제 | ✅ | https://www.ajunews.com/rss/sokbo.xml | 전체 | 802 |
| 파이낸셜뉴스 | ✅ | https://www.fnnews.com/rss/r20/fn_realnews_all.xml | 전체 | 372 |
| 헤럴드경제 | ✅ | https://biz.heraldcorp.com/rss/google/newsAll | 전체 | 300 |
| 이투데이 | ✅ | https://rss.etoday.co.kr/eto/etoday_news_all.xml | 전체 | 231 |
| 아시아경제 | ✅ | https://view.asiae.co.kr/rss/all.htm | 전체 | 100 |
| 머니투데이 | ✅ | http://rss.mt.co.kr/mt_news.xml | 전체 | 100 |
| 조선비즈 | ✅ | https://biz.chosun.com/arc/outboundfeeds/rss/?outputType=xml | 전체 | 100 |
| 한국경제 | ✅ | https://www.hankyung.com/feed/all-news | 전체 | 50 |
| 서울경제 | ✅ | https://www.sedaily.com/rss/newsall | 전체 | 50 |
| 이데일리 | ✅ | http://rss.edaily.co.kr/edaily_news.xml | 전체 | 50 |
| EBN | ✅ | https://cdn.ebn.co.kr/rss/gns_allArticle.xml | 전체 | 50 |
| 서울파이낸스 | ✅ | https://cdn.seoulfn.com/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 브릿지경제 | ✅ | https://www.viva100.com/rssAll.xml | 전체 | 50 |
| 메트로 | ✅ | https://www.metroseoul.co.kr/news/rss | 전체 | 50 |
| 매일경제 | ✅ | https://www.mk.co.kr/rss/30000001/ | 섹션(헤드라인) | 50 |
| 프라임경제 | ✅ | https://www.newsprime.co.kr/data/rss/news.xml | 전체 | 25 |
| 조세일보 | ✅ | https://www.joseilbo.com/Contents/rss/rss_total.php | 전체 | 20 |
| 머니S | ❌ | — | — | — |
| 비즈워치 | ❌ | — | — | — |
| 뉴스핌 | ❌ | — | — | — |
| 데일리안 | ❌ | — | — | — |
| 글로벌이코노믹 | ❌ | — | — | — |
| 인베스트조선 | ❌ | — | — | — |

## IT / 과학 / 전문

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| IT동아 | ✅ | https://it.donga.com/feeds/rss/ | 전체 | 100 |
| 아이뉴스24 | ✅ | https://www.inews24.com/rss/news_all.xml | 전체 | 100 |
| 블로터 | ✅ | https://cdn.bloter.net/rss/gns_allArticle.xml | 전체 | 50 |
| 테크M | ✅ | https://www.techm.kr/rss/allArticle.xml | 전체 | 50 |
| 전자신문 | ✅ | https://rss.etnews.com/Section901.xml | 섹션 | 30 |
| 지디넷코리아 | ✅ | https://feeds.feedburner.com/zdkorea | 전체 | 30 |
| 바이라인네트워크 | ✅ | https://byline.network/feed/ | 전체 | 20 |
| 보안뉴스 | ✅ | https://www.boannews.com/media/news_rss.xml | 전체 | 10 |
| 코메디닷컴 | ✅ | https://kormedi.com/feed/ | 전체 | 10 |
| 디지털데일리 | ❌ | — | — | — |
| 디지털타임스 | ❌ | — | — | — |
| 동아사이언스 | ❌ | — | — | — |

## 통신사

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 연합뉴스 | ✅ | https://www.yna.co.kr/rss/news.xml | 전체 | 120 |
| 뉴시스 | ✅ | https://www.newsis.com/RSS/sokbo.xml | 섹션(속보) | 100 |
| 뉴스1 | ❌ | — | — | — |

## 방송

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| SBS | ✅ | https://news.sbs.co.kr/news/newsflashRssFeed.do | 섹션(속보) | 101 |
| TV조선 | ✅ | https://news.tvchosun.com/site/data/rss/rss.xml | 전체 | 50 |
| MBN | ✅ | https://www.mbn.co.kr/rss/politics/ | 섹션 | 30 |
| JTBC | ✅ | https://fs.jtbc.co.kr/RSS/newsflash.xml | 섹션(속보) | 20 |
| 연합뉴스TV | ✅ | https://www.yonhapnewstv.co.kr/browse/feed/ | 전체 | 11 |
| KBS | ❌ | — | — | — |
| MBC | ❌ | — | — | — |
| YTN | ❌ | — | — | — |
| 채널A | ❌ | — | — | — |

## 인터넷 / 시사

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 미디어오늘 | ✅ | http://www.mediatoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 노컷뉴스 | ✅ | https://rss.nocutnews.co.kr/news/news.xml | 전체 | 50 |
| 폴리뉴스 | ✅ | https://www.polinews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 시사IN | ✅ | https://www.sisain.co.kr/rss/allArticle.xml | 전체 | 50 |
| 시사저널 | ✅ | https://www.sisajournal.com/rss/allArticle.xml | 전체 | 50 |
| 한겨레21 | ✅ | https://h21.hani.co.kr/rss/ | 전체 | 30 |
| 프레시안 | ✅ | https://www.pressian.com/api/v3/site/rss/news | 전체 | 25 |
| 오마이뉴스 | ✅ | http://rss.ohmynews.com/rss/ohmynews.xml | 전체 | 20 |
| 데일리NK | ✅ | https://www.dailynk.com/feed/ | 전체 | 10 |
| 주간경향 | ✅ | https://weekly.khan.co.kr/rss/rssdata/world_news.xml | 섹션 | 50 |
| 뉴데일리 | ❌ | — | — | — |
| 미디어펜 | ❌ | — | — | — |
| 민중의소리 | ❌ | — | — | — |
| 뉴스타파 | ❌ | — | — | — |

## 보험 / 금융 전문지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 한국보험신문 | ✅ | https://www.insnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 보험매일 | ✅ | https://www.fins.co.kr/rss/allArticle.xml | 전체 | 50 |
| 보험저널 | ✅ | https://www.insjournal.co.kr/rss/allArticle.xml | 전체 | 50 |
| 대한금융신문 | ✅ | https://www.kbanker.co.kr/rss/allArticle.xml | 전체 | 50 |
| 금융소비자뉴스 | ✅ | https://www.newsfc.co.kr/rss/allArticle.xml | 전체 | 50 |
| 파이낸셜투데이 | ✅ | https://www.ftoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 인슈넷 | ❌ | — | — | — |
| 보험소비자신문 | ❌ | — | — | — |
| 한국금융신문 | ❌ | — | — | — |
| 팍스넷뉴스 | ❌ | — | — | — |
| 더벨 | ❌ | — | — | — |

## 의약 / 바이오

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 청년의사 | ✅ | https://www.docdocdoc.co.kr/rss/allArticle.xml | 전체 | 50 |
| 의협신문 | ✅ | https://www.doctorsnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 히트뉴스 | ✅ | https://www.hitnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 라포르시안 | ✅ | https://www.rapportian.com/rss/allArticle.xml | 전체 | 50 |
| 팜뉴스 | ✅ | https://www.pharmnews.com/rss/allArticle.xml | 전체 | 50 |
| 메디게이트뉴스 | ❌ | — | — | — |
| 데일리팜 | ❌ | — | — | — |
| 약업신문 | ❌ | — | — | — |
| 메디칼타임즈 | ❌ | — | — | — |

## 건설 / 부동산 / 에너지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 대한전문건설신문 | ✅ | https://www.koscaj.com/rss/allArticle.xml | 전체 | 50 |
| 하우징헤럴드 | ✅ | https://www.housingherald.co.kr/rss/allArticle.xml | 전체 | 50 |
| 이투뉴스 | ✅ | https://www.e2news.com/rss/allArticle.xml | 전체 | 50 |
| 그린포스트코리아 | ✅ | https://www.greenpostkorea.co.kr/rss/allArticle.xml | 전체 | 50 |
| 투데이에너지 | ✅ | https://www.todayenergy.kr/rss/allArticle.xml | 전체 | 50 |
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
| 베리타스알파 | ✅ | https://www.veritas-a.com/rss/allArticle.xml | 전체 | 50 |
| 법률신문 | ✅ | https://cdn.lawtimes.co.kr/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 매일노동뉴스 | ✅ | https://www.labortoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 한국교육신문 | ✅ | https://www.hangyo.com/data/rss/news.xml | 전체 | 25 |

## 농업 / 환경

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 한국농정신문 | ✅ | https://www.ikpnews.net/rss/allArticle.xml | 전체 | 50 |
| 농수축산신문 | ✅ | https://www.aflnews.co.kr/rss/allArticle.xml | 전체 | 50 |
| 농민신문 | ❌ | — | — | — |

## 스포츠 / 연예

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 스포츠조선 | ✅ | https://www.sportschosun.com/rss/index_all.htm | 전체 | 100 |
| 일간스포츠 | ✅ | https://isplus.com/rss | 전체 | 100 |
| OSEN | ✅ | https://rss.mt.co.kr/osen_news.xml | 전체 | 49 |
| 텐아시아 | ✅ | https://www.tenasia.co.kr/rss/music/ | 섹션 | 50 |
| 스포츠동아 | ❌ | — | — | — |
| 스포츠서울 | ❌ | — | — | — |
| 마이데일리 | ❌ | — | — | — |
| 스타뉴스 | ❌ | — | — | — |
| 뉴스엔 | ❌ | — | — | — |

## 지역지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| 인천일보 | ✅ | https://www.incheonilbo.com/rss/allArticle.xml | 전체 | 50 |
| 경남도민일보 | ✅ | https://www.idomin.com/rss/allArticle.xml | 전체 | 50 |
| 충청투데이 | ✅ | https://www.cctoday.co.kr/rss/allArticle.xml | 전체 | 50 |
| 대전일보 | ✅ | https://www.daejonilbo.com/rss/allArticle.xml | 전체 | 50 |
| 강원도민일보 | ✅ | https://www.kado.net/rss/allArticle.xml | 전체 | 50 |
| 전북일보 | ✅ | https://www.jjan.kr/news/rssAll | 전체 | 50 |
| 전남일보 | ✅ | https://cdn.jnilbo.com/rss/gn_rss_allArticle.xml | 전체 | 50 |
| 제주일보 | ✅ | https://www.jejunews.com/rss/allArticle.xml | 전체 | 50 |
| 한라일보 | ✅ | https://www.ihalla.com/rss.php?section=73 | 섹션 | 30 |
| 부산일보 | ❌ | — | — | — |
| 국제신문 | ❌ | — | — | — |
| 매일신문 | ❌ | — | — | — |
| 영남일보 | ❌ | — | — | — |
| 강원일보 | ❌ | — | — | — |
| 중도일보 | ❌ | — | — | — |
| 경남신문 | ❌ | — | — | — |
| 광주일보 | ❌ | — | — | — |
| 무등일보 | ❌ | — | — | — |
| 경기일보 | ❌ | — | — | — |

## 영자지

| 언론사 | RSS | 피드 URL | 범위 | 항목수 |
|--------|:---:|----------|------|-------:|
| The Korea Times | ✅ | https://feed.koreatimes.co.kr/k/allnews.xml | 전체 | 65 |
| The Korea Herald | ✅ | https://www.koreaherald.com/rss/newsAll | 전체 | 50 |
| Korea JoongAng Daily | ❌ | — | — | — |

## 해외 (재)보험 전문지

| 매체 | RSS | 피드 URL | 범위 | 항목수 |
|------|:---:|----------|------|-------:|
| Reinsurance News | ✅ | https://www.reinsurancene.ws/feed/ | 전체 | 10 |

## 섹션별 피드 다중 등록

`범위`가 **섹션**인 곳(매일경제, 전자신문, SBS, MBN, 뉴시스, 주간경향, 텐아시아, 한라일보)은
전체 통합 피드 대신 섹션별 피드를 제공한다. 여러 섹션을 각각 소스로 등록하면 커버리지를
넓힐 수 있다(패턴은 각 사이트마다 다름):

- 매일경제: `.../rss/<섹션코드>/` — 30000001(헤드라인), 40300001(경제) 등 섹션코드 치환
- 전자신문: `https://rss.etnews.com/Section<번호>.xml`
- 서울경제: `https://www.sedaily.com/rss/<economy|finance|politics|society|...>` (전체는 `newsall`)
- 노컷뉴스: `https://rss.nocutnews.co.kr/category/<politics|economy|society|world|...>.xml`
- MBN: `https://www.mbn.co.kr/rss/<politics|economy|society|...>/`

## ❌ 표시에 대해

❌ 는 "이 언론사가 영원히 RSS가 없다"가 아니라, **2026-08-20 검증 시점에 흔히 쓰이던
피드 경로들에서 살아있는 공개 RSS를 확인하지 못했다**는 뜻이다. 원인은 대체로 (1) 과거
피드 URL이 404 또는 HTML 안내페이지로 바뀜, (2) 피드 전용 호스트의 DNS 소멸, (3) 홈페이지가
JS 렌더링 SPA라 피드 링크를 정적으로 노출하지 않음, (4) RSS 제공 중단이다. 특히 (3)에 걸린
곳(중앙일보, 한국일보, KBS, MBC, YTN, 대형 지역지 상당수)은 실제로는 RSS가 있어도 이
자동 검증으로는 못 잡은 것일 수 있으니, 정확한 피드 경로가 확인되면 해당 행을 ✅ 로 갱신하면
된다. RSS가 정말 없는 곳은 newswatch의 `--kind crawl`(CSS 셀렉터 크롤) 어댑터로 붙일 수 있다.

## 등록 예시

```sh
newswatch add-source "연합뉴스" https://www.yna.co.kr/rss/news.xml --kind rss
newswatch add-source "조선일보" "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml" --kind rss
newswatch add-source "한국보험신문" https://www.insnews.co.kr/rss/allArticle.xml --kind rss --topic insurance
```
