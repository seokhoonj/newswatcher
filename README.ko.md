# newswatcher

[![check](https://github.com/seokhoonj/newswatcher/actions/workflows/check.yml/badge.svg)](https://github.com/seokhoonj/newswatcher/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/newswatcher)](https://pypi.org/project/newswatcher/)
[![Python](https://img.shields.io/pypi/pyversions/newswatcher)](https://pypi.org/project/newswatcher/)
[![License](https://img.shields.io/pypi/l/newswatcher)](https://github.com/seokhoonj/newswatcher/blob/main/LICENSE)

[English](README.md) | **한국어**

newswatcher는 RSS 피드와 robots 정책이 허용하는 목록 페이지를 확인하고, 새로운 기사를
사용자가 정의한 토픽과 매칭한 뒤 LLM으로 요약하여 토픽별 다이제스트 한 통을 이메일이나
채팅으로 보냅니다. 전송은 선택 사항입니다 — 코어는 수집·요약·아카이브만으로 동작하고,
이메일과 챗은 선택 애드온(`newswatcher[email]` / `newswatcher[chat]`)입니다. 같은 사건을
여러 매체가 보도하면 한 항목으로 묶습니다. 토픽은 직접
정의하므로 같은 도구로 종목, 기술, 정책, 그 밖에 피드가 다루는 어떤 주제든 추적할 수
있습니다.

## 1. 설치

newswatcher는 Python 3.11 이상이 필요합니다. 코어(수집·요약·아카이브)는 단독으로 설치되고,
발송은 선택 사항이라 원하는 채널만 추가합니다:

```sh
pip install newswatcher            # 코어: 수집·요약·아카이브 (articles로 조회)
pip install "newswatcher[email]"   # + 이메일 다이제스트 (mailmail)
pip install "newswatcher[chat]"    # + 챗 다이제스트 (pushpush)
pip install "newswatcher[all]"     # + 둘 다
```

아래 빠른 시작은 코어 `newswatcher`만 있으면 됩니다 — 이메일·챗은 나중에(전송) 추가합니다.

## 2. 빠른 시작

아래 명령들은 터미널(Terminal·PowerShell·명령 프롬프트 — 파이썬 프롬프트가 아님)에서
실행합니다. 먼저 [Google AI Studio](https://aistudio.google.com/apikey)에서 무료 Gemini
API 키(LLM 서비스 업체가 주는 인증 키)를 발급받고(구글 로그인 → **Create API key** → 복사),
저장합니다 — 입력값은 화면에 표시되지 않습니다:

```sh
newswatcher set-key gemini
```

토픽과 RSS 소스를 등록하고 한 번 실행한 뒤 요약을 바로 읽습니다 — 첫 결과를 보는 데는
이메일 설정이 필요 없습니다:

```sh
newswatcher add-topic 증시 --include 코스피 금리 실적 반도체 --exclude 연예
newswatcher add-source 한국경제 "https://www.hankyung.com/feed/all-news" --kind rss --topic 증시
newswatcher poll --no-mail
newswatcher articles
```

`articles`에 아무것도 안 나오면 아직 토픽에 맞는 새 기사가 없었던 것뿐입니다 — 오류가 아니라
정상입니다. `--include` 키워드를 넓히거나 잠시 후 다시 `poll` 하세요.

토픽은 피드의 언어로 매칭하므로 키워드도 피드 언어에 맞춥니다. 한국어 피드에는 한국어
키워드를, 영어 피드에는 영어 키워드를 씁니다. `newswatcher topics`·`newswatcher sources`로
등록 내용을 확인합니다.

`articles`로 읽는 대신 **이메일**이나 **챗**으로 받으려면 전송 extra를 설치하고 채널을 한 번
설정합니다 — [전송](#4-전송) 참고.

## 3. 명령

전체 옵션은 `newswatcher --help` 또는 `newswatcher <command> --help`에서 확인하고,
`newswatcher --version`은 버전을 출력합니다.

| 명령 | 하는 일 |
|------|---------|
| `add-topic <name> [--include WORD...] [--exclude WORD...]` | 토픽 필터 정의: 이름 + `--include` 키워드(하나라도 있으면 매칭) + 선택 `--exclude` 키워드(하나라도 있으면 제외). include가 비면 모든 기사 매칭. |
| `topics` | 정의된 토픽을 include / exclude 키워드와 함께 나열. |
| `add-category <name> [--hint TEXT]` | 분류 카테고리 정의: 이름 + 무엇이 이 카테고리에 속하는지 설명하는 선택 `--hint`. 요약 시 LLM이 각 기사를 정의된 카테고리 하나로 분류하며, 응답 첫 줄에 정의된 카테고리 이름이 없으면 빈 값으로 저장합니다(`categories.toml` 참고). |
| `categories` | 정의된 카테고리를 hint와 함께 나열. |
| `add-source <name> <url> [--kind rss\|crawl] [--topic NAME]... [--keep-all]` | 소스 등록 — RSS 피드(`--kind rss`) 또는 robots 허용 크롤 페이지(`--kind crawl`) — 와 테스트할 `--topic`들. crawl 소스는 selector 필요: `--item --title --link`(필수), `--date --body-selector`(선택). `--keep-all`은 키워드 필터 없이 소스의 모든 기사 보관(피드 전체가 온토픽인 전문지용). |
| `sources` | 등록된 소스를 kind·URL·토픽과 함께 나열. |
| `set-key <provider>` | LLM provider의 API 키를 에코 없이 입력받아 thinchat 자체 자격증명 저장소에 저장. provider는 `gemini`·`openai`·`claude`; 키는 같은 이름의 `*_API_KEY` 환경 변수에서도 읽으며 그쪽이 우선. |
| `setup [--provider P]` | 각 채널의 빠진 비밀을 한 번의 안내식 패스로 채움 — LLM 키는 thinchat, 이메일 비번은 mailmail, 챗 토큰은 pushpush에. 에코 없이 입력받고 각각 어디에 저장됐는지 출력. 이미 설정된 것은 건너뛰고, 계정·라우트가 아직 없는 채널은 해당 도구로 안내. |
| `doctor [--provider P]` | 각 비밀과 설정 파일이 어디 있고 설정됐는지를 비밀 값 출력 없이 표시. 설정된 채널에 비밀이 없거나 저장소를 읽을 수 없으면 non-zero로 종료하므로, 예약 실행이 설정 완료 여부를 게이트로 쓸 수 있음. |
| `recent <url> [--limit N]` | 피드 최신 항목(제목+링크)을 저장·요약 없이 출력 — 등록 전 URL 확인용. `--limit N`으로 개수 제한. |
| `poll` | 한 번의 패스: 전 소스 fetch → 토픽에 맞는 새로운 기사만 요약·아카이브 → 다이제스트 발송. `--to`/`--push`=목적지, `--no-mail`=발송 없이 수집만, `--no-store`=아카이브 안 함, `--store-body`=각 기사 본문도 별도 로컬 저장소에 보관, `--no-heal`=selector 복구 생략, `--provider`/`--model`=LLM 선택. |
| `watch [--every N]` | `poll`을 포그라운드에서 `--every` 분(기본 30)마다 반복, 중단할 때까지. poll의 모든 옵션을 받음. |
| `articles [--topic NAME] [--since DATE] [--until DATE]` | 아카이브 기사(제목·우리 요약·링크)를 나열, 토픽·반열림 `[since, until)` 날짜 범위로 필터 가능. |
| `heal [--dry-run] [--provider P] [--model M]` | selector가 끊긴 crawl 소스를 점검해 LLM으로 복구(라이브 페이지로 검증). `--dry-run`은 제안만 보고 쓰지 않음. |
| `schedule install\|status\|remove [--every N]` | 반복 poll을 OS 스케줄러에 설치·조회·제거(Linux/macOS는 cron, Windows는 schtasks). `--every N`으로 간격 설정. |

## 4. 전송

다이제스트는 이메일, 채팅, 또는 둘 다로 보낼 수 있습니다. 원하는 대상을 하나 이상
설정합니다. 각 채널은 선택 extra(`newswatcher[email]` / `newswatcher[chat]`)이고, 동반
패키지가 각자 자기 자격증명을 자기 저장소에 관리하므로 newswatcher는 당신의 이메일 비번이나
봇 토큰을 저장하지 않습니다. 둘 다 없어도 수집·요약·아카이브는 되며, 아카이브는
`newswatcher articles`로 봅니다.

- 이메일은 mailmail 패키지(`newswatcher[email]`)로 보냅니다. 계정(또는 주소록 별칭)을 mailmail
  자체 CLI(`mailmail --help`)로 한 번 설정한 뒤, `--to ADDRESS`(또는 `NEWSWATCHER_DIGEST_TO`
  설정)로 그 별칭이나 일반 주소를 지정합니다.
- 채팅은 pushpush 패키지(`newswatcher[chat]`)로 보냅니다. 라우트(봇 + 목적지 —
  텔레그램·슬랙·디스코드)를 pushpush 자체 CLI(`pushpush --help`)로 한 번 설정한 뒤,
  `--push ROUTE`(또는 `NEWSWATCHER_DIGEST_PUSH` 설정)로 그 라우트를 지정합니다. 다이제스트는
  markdown 메시지 한 통으로 전송됩니다.

즉 newswatcher는 자기 비밀을 하나도 갖지 않습니다: LLM 키는 thinchat, 이메일 비번은
mailmail, 챗 토큰은 pushpush에 — 각 도구를 단독으로 쓸 때와 똑같이 각자 저장소에 있습니다.
`newswatcher setup`으로 한 번에 안내식으로 설정하고, `newswatcher doctor`로 무엇이 어디에
설정돼 있는지 전체 지도를 확인합니다.

## 5. 뉴스 피드

유효한 RSS/Atom 피드는 무엇이든 소스가 됩니다. 아래는 검증된 국내 피드의 대표
목록이고, 섹션별로 나누고 검증 시점에 살아 있던 피드를 표시한 전체 목록은
[docs/korean-news-rss.md](docs/korean-news-rss.md)에 있습니다. 피드가 없는 사이트는
`--kind crawl` 소스로 붙일 수 있습니다.

| 언론사 | 분야 | 피드 URL |
|--------|------|----------|
| 연합뉴스 | 통신 | `https://www.yna.co.kr/rss/news.xml` |
| 한국경제 | 경제 | `https://www.hankyung.com/feed/all-news` |
| 조선비즈 | 경제 | `https://biz.chosun.com/arc/outboundfeeds/rss/?outputType=xml` |
| 매일경제 | 경제 | `https://www.mk.co.kr/rss/30000001/` |
| 이데일리 | 경제 | `http://rss.edaily.co.kr/edaily_news.xml` |
| 머니투데이 | 경제 | `http://rss.mt.co.kr/mt_news.xml` |
| 전자신문 | IT | `https://rss.etnews.com/Section901.xml` |
| 지디넷코리아 | IT | `https://feeds.feedburner.com/zdkorea` |
| The Korea Herald | 영문 | `https://www.koreaherald.com/rss/newsAll` |
| The Korea Times | 영문 | `https://feed.koreatimes.co.kr/k/allnews.xml` |

검증된 해외(영어) 피드의 대표 목록은 아래와 같고, 카테고리별로 나누고 어느 매체가 본문을
페이월로 막는지 표시한 전체 목록은 [docs/world-news-rss.md](docs/world-news-rss.md)에
있습니다. 이 피드에는 영어 토픽 키워드를 씁니다.

| 매체 | 분야 | 피드 URL |
|------|------|----------|
| BBC News | 통신 | `https://feeds.bbci.co.uk/news/world/rss.xml` |
| The Guardian | 통신 | `https://www.theguardian.com/world/rss` |
| Al Jazeera | 통신 | `https://www.aljazeera.com/xml/rss/all.xml` |
| The New York Times | 국제 | `https://rss.nytimes.com/services/xml/rss/nyt/World.xml` |
| CNBC | 경제 | `https://www.cnbc.com/id/100003114/device/rss/rss.html` |
| MarketWatch | 경제 | `http://feeds.marketwatch.com/marketwatch/topstories/` |
| TechCrunch | IT | `https://techcrunch.com/feed/` |
| The Verge | IT | `https://www.theverge.com/rss/index.xml` |
| Nature | 과학 | `https://www.nature.com/nature.rss` |

## 6. 설정 파일

newswatcher는 직접 편집하는 설정을 `$XDG_CONFIG_HOME/newswatcher`에 저장합니다.
`XDG_CONFIG_HOME`이 없으면 `~/.config/newswatcher`를 사용합니다. CLI도 같은 파일을
쓰므로 CLI 등록과 직접 편집을 함께 사용할 수 있습니다. CLI는 항목을 덧붙이거나
제자리에서 고칠 뿐이라, 손으로 넣은 주석과 서식은 그대로 보존됩니다.

`topics.toml`에는 토픽 필터를 작성합니다. 기사 제목이나 피드 요약에 include 키워드가
하나라도 있고 exclude 키워드는 하나도 없을 때 매칭됩니다. `includes`가 비어 있으면
모든 기사가 매칭됩니다.

```toml
[[topic]]
name = "증시"
includes = ["코스피", "금리", "실적", "반도체"]
excludes = ["연예"]

[[topic]]
name = "반도체"
includes = ["반도체", "파운드리", "HBM", "TSMC", "엔비디아"]
```

`categories.toml`(선택)에는 분류 라벨을 작성합니다. 파일이 있으면 요약을 쓰는 바로 그
LLM 호출에서(추가 비용 없이) 각 기사를 카테고리 하나로 분류해(응답 첫 줄에 정의된 카테고리
이름이 없으면 빈 값) 기사에 저장합니다. 토픽(무엇을
*보관*할지 정하는 키워드 필터)과 달리 카테고리는 표시용 그룹 라벨이며, 모델이 맥락으로
고릅니다(그래서 "감독기관이 나눔 행사를 열었다"가 키워드 방식처럼 규제로 오분류되지 않습니다).
각 항목은 `name`과, 모델을 안내하는 선택 `hint`입니다. 파일이 없으면 분류는 꺼지고 카테고리는
빈 값이 됩니다.

```toml
[[category]]
name = "M&A"
hint = "인수합병, 매각, 지분·경영권 거래"

[[category]]
name = "기타"
hint = "위에 안 맞는 나눔·인사·행사 등 일반"
```

`sources.toml`에는 RSS 또는 crawl 소스를 작성합니다. `topics`는 해당 소스에 적용할
토픽 필터를 지정합니다. 소스의 모든 기사를 키워드 필터 없이 보관하려면
`keep_all = true`를 설정합니다.

```toml
[[source]]
name = "한국경제"
kind = "rss"
url = "https://www.hankyung.com/feed/all-news"
topics = ["증시", "반도체"]

[[source]]
name = "거래소-공시"
kind = "crawl"
url = "https://example.com/markets/notices"
topics = ["증시"]
item = "article.news-item"
title = "h2"
link = "a@href"
date = "time"
body_selector = "main article"
```

crawl 소스에는 `item`, `title`, `link` selector (HTML에서 원하는 요소를 고르는
표현식)가 필요하며 `date`와 `body_selector`는 선택 사항입니다. URL이 속성에 들어
있으면 link selector에 `css@attribute` 형식을 사용합니다.

비밀이 아닌 설정은 `config.toml`에도 둘 수 있습니다. 환경 변수가 같은 설정 파일
값보다 우선합니다. 예를 들어 `NEWSWATCHER_DIGEST_TO`는 `digest_to`에, `NEWSWATCHER_DIGEST_PUSH`는
`digest_push`에 대응합니다. `NEWSWATCHER_DEDUP_THRESHOLD`(`dedup_threshold`, 0.0~1.0, 기본 0.5)은
두 헤드라인이 얼마나 비슷해야 한 사건으로 묶일지를 정합니다 — 높이면 덜 묶고, 낮추면 더 묶습니다.
기사 archive (지속적으로 보관하는 기록)와 실행 상태는 XDG data/state 디렉터리를
사용하며, `NEWSWATCHER_DATA_DIR`와 `NEWSWATCHER_STATE_DIR`로 위치를 바꿀 수 있습니다.
archive는 기본적으로 아무것도 지우지 않습니다. 오래된 기록을 정리하려면
`NEWSWATCHER_ARCHIVE_KEEP_DAYS`(`archive_keep_days`, 양의 정수)를 설정하세요 — 각
poll이 다이제스트 발송 후 그보다 오래된 기사를 삭제합니다. 미설정이면 무한 보관합니다
(이 삭제는 되돌릴 수 없으니 의도적으로만 켜세요). `NEWSWATCHER_STORE_BODY`(`store_body`,
불리언)는 `--store-body` 플래그 없이도 본문 캡처를 켭니다 — 켜면 각 기사 본문을 data
디렉터리 아래 별도 `bodies` 폴더(`archive`의 형제)에 보관합니다(재요약·원문 보관용). 기본은
꺼짐이고, 저장된 본문은 로컬 전용이라 발송되지 않습니다. 저장된 본문은 (기사 아카이브와 달리)
자동 삭제되지 않으므로 정리는 사용자 몫이며, `--no-store`와 함께 쓰면 본문에 대응하는 아카이브
기사가 없습니다.

## 7. provider 키와 모델

**provider**는 요약을 작성하는 LLM 서비스입니다. newswatcher는 네 곳을 지원하며, 왼쪽 열의
이름을 `--provider`나 `set-key`에 넘깁니다:

| provider | 키(환경 변수) | 키 발급처 |
|----------|---------------|-----------|
| `gemini` (기본) | `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) — 무료 티어 |
| `openai` | `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) |
| `claude` | `CLAUDE_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `ollama` | — (로컬 실행) | 키 불필요 |

provider 키는 비밀이며, newswatcher가 아니라 요약에 쓰는 thinchat 라이브러리의
저장소에 있습니다. `setup`(이메일·챗까지 같은 패스에서 설정) 또는 키만 넣는 `set-key`로
한 번 저장하며, 둘 다 에코 없이 입력받아 thinchat 자체 자격증명 저장소에 씁니다.

```sh
newswatcher setup            # LLM 키 + 이메일 + 챗을 한 번에
newswatcher set-key gemini   # LLM 키만
```

각 키는 위 표의 환경 변수에서도 읽으며 환경 변수가 우선하므로, 아무것도 저장하지 않고
일회성으로 키를 넣을 수 있습니다.

newswatcher는 기본적으로 Gemini 무료 티어로 요약합니다. 다른 provider(그리고 원하면
특정 모델)는 `--provider` / `--model`로 고르거나, `NEWSWATCHER_LLM_PROVIDER` /
`NEWSWATCHER_LLM_MODEL` 설정(`config.toml`의 `llm_provider`, `llm_model`)으로
지속 지정합니다.

```sh
newswatcher poll --provider claude --model claude-sonnet-5
export NEWSWATCHER_LLM_PROVIDER=openai
```

## 8. 책임 있는 수집

모든 피드, 목록 페이지, 기사 요청은 전송 전에 사이트의 robots 정책을 확인하며
newswatcher의 user agent (HTTP 요청에서 프로그램을 식별하는 문자열)를 보냅니다.
허용되지 않은 URL은 요청하지 않습니다. 지속 archive와 발송 다이제스트에는 LLM이 작성한
요약, 원문 링크, 메타데이터만 들어갑니다. 원문 본문은 일시적인 요약 입력이라 발송되지 않고
기사 archive에도 들어가지 않습니다. `--store-body`(또는 `NEWSWATCHER_STORE_BODY`)로
켤 때만 별도 `bodies` 저장소에 보관됩니다.

## 9. 스케줄링

30분마다 실행하는 반복 poll을 운영체제 스케줄러(정해진 시각에 명령을 실행하는
OS 기능)에 설치합니다.

```sh
newswatcher schedule install
```

분, `Nm`, `Nh` 형식으로 다른 주기를 지정할 수 있으며 작업 상태 확인과 삭제도
지원합니다.

```sh
newswatcher schedule install --every 2h
newswatcher schedule status
newswatcher schedule remove
```

스케줄링은 Linux·macOS에서 `crontab`, Windows에서 `schtasks`를 사용합니다.
Windows에서는 하루 미만의 임의 간격이 동작하고(`--every 45`, `--every 5h`),
Linux·macOS의 cron은 나눠떨어지는 간격(15/20/30분, 1/2/4/8/12시간, 하루)만 실행하며
그 외 간격은 잘못 예약하지 않고 거부합니다. 예약 실행도 대화형 poll과 같은 설정을
사용하므로, LLM 키가 (thinchat 저장소 또는 환경 변수로) 닿는지와 `config.toml`에
저장하지 않은 설정이 예약 실행 환경에 제공되는지 확인해야 합니다. `newswatcher doctor`로
예약 전에 확인할 수 있습니다.

Windows에서는 설치한 사용자의 대화형 세션으로 작업이 등록되므로, 아무도 로그인하지
않은 상태에서는 발화하지 않습니다(화면 잠금은 괜찮지만 로그인 화면은 아닙니다). 또한
작업 스케줄러 기본값에 따라 배터리 전원에서는 시작하지 않습니다. 확인은
`schtasks /Query /TN newswatcher-poll`로 합니다. Linux·macOS의 cron 작업에는 두 제약이
모두 없습니다.

poll은 단일 인스턴스 lock을 잡으므로 예약 poll과 수동 poll이 동시에 돌지 않습니다.
나중에 시작한 쪽은 이미 poll이 실행 중이라고 알리고 종료합니다. lock은 Linux·macOS에서
`flock`, Windows에서 `msvcrt`를 씁니다.

## 10. AI 코딩 에이전트에서 사용

이 저장소에는 `poll` skill이 있습니다: "뉴스 확인해줘", "내 newswatcher 폴 돌려줘"처럼
말하면 한 번 poll을 실행하고 결과를 전달합니다.

### Claude Code

Claude Code 채팅창에서 마켓플레이스를 추가하고 설치합니다:

```
/plugin marketplace add seokhoonj/newswatcher
/plugin install newswatcher@newswatcher
```

그다음 `/newswatcher:poll`(또는 자연어)로 호출합니다. skill은 `newswatcher` 명령을 부르므로
패키지도 설치돼 있어야 합니다(`pip install newswatcher`). 자세한 것은
`plugins/newswatcher/skills/poll/SKILL.md`.

### Codex

터미널에서 마켓플레이스를 추가하고 설치합니다:

```
codex plugin marketplace add seokhoonj/newswatcher
codex plugin add newswatcher@newswatcher
```

`poll` skill이 관련 요청에 자동으로 반응합니다.

### 플러그인 없이 (symlink)

skill을 스킬 폴더에 심링크해 `/poll`로 부릅니다:

```sh
ln -s "$PWD/plugins/newswatcher/skills/poll" ~/.claude/skills/poll   # Claude Code → /poll
ln -s "$PWD/plugins/newswatcher/skills/poll" ~/.codex/skills/poll    # Codex → $newswatcher:poll
```

Claude Code는 바로 인식하고, Codex는 재시작해야 로딩됩니다.

## 11. 라이선스

[MIT](LICENSE)
