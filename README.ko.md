# newswatcher

[English](README.md) | **한국어**

newswatcher는 RSS 피드와 robots 정책이 허용하는 목록 페이지를 확인하고, 새 기사를
사용자가 정의한 토픽과 매칭한 뒤 LLM으로 요약하여 토픽별 다이제스트 한 통을 이메일이나
채팅으로 보냅니다. 같은 사건을 여러 매체가 보도하면 한 항목으로 묶습니다. 토픽은 직접
정의하므로 같은 도구로 종목, 기술, 정책, 그 밖에 피드가 다루는 어떤 주제든 추적할 수
있습니다.

## 설치

newswatcher는 Python 3.11 이상이 필요합니다.

```sh
pip install newswatcher
```

## 빠른 시작

토픽과 RSS 소스를 등록하고, 다이제스트 수신 주소와 기본 Gemini LLM provider
(LLM 서비스를 제공하는 업체)용 API 키를 설정한 다음 한 번 poll을 실행합니다.

```sh
newswatcher add-topic 증시 --include 코스피 금리 실적 반도체 --exclude 연예
newswatcher add-source 한국경제 https://www.hankyung.com/feed/all-news \
  --kind rss --topic 증시
export NEWSWATCHER_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatcher poll
```

토픽은 피드의 언어로 매칭하므로 키워드도 피드 언어에 맞춥니다. 한국어 피드에는 한국어
키워드를, 영어 피드에는 영어 키워드를 씁니다.

`newswatcher topics`와 `newswatcher sources`로 등록 내용을 확인할 수 있습니다. 전체
명령과 옵션은 `newswatcher --help` 또는 `newswatcher <command> --help`에서 확인합니다.

## 명령

전체 옵션은 `newswatcher --help` 또는 `newswatcher <command> --help`에서 확인하고,
`newswatcher --version`은 버전을 출력합니다.

| 명령 | 하는 일 |
|------|---------|
| `add-topic <name> [--include WORD...] [--exclude WORD...]` | 토픽 필터 정의: 이름 + `--include` 키워드(하나라도 있으면 매칭) + 선택 `--exclude` 키워드(하나라도 있으면 제외). include가 비면 모든 기사 매칭. |
| `topics` | 정의된 토픽을 include / exclude 키워드와 함께 나열. |
| `add-source <name> <url> [--kind rss\|crawl] [--topic NAME]... [--keep-all]` | 소스 등록 — RSS 피드(`--kind rss`) 또는 robots 허용 크롤 페이지(`--kind crawl`) — 와 테스트할 `--topic`들. crawl 소스는 selector 필요: `--item --title --link`(필수), `--date --body-selector`(선택). `--keep-all`은 키워드 필터 없이 소스의 모든 기사 보관(피드 전체가 온토픽인 전문지용). |
| `sources` | 등록된 소스를 kind·URL·토픽과 함께 나열. |
| `recent <url> [--limit N]` | 피드 최신 항목(제목+링크)을 저장·요약 없이 출력 — 등록 전 URL 확인용. `--limit N`으로 개수 제한. |
| `poll` | 한 번의 패스: 전 소스 fetch → 토픽에 맞는 새 기사만 요약·아카이브 → 다이제스트 발송. `--to`/`--push`=목적지, `--no-mail`=발송 없이 수집만, `--no-store`=아카이브 안 함, `--no-heal`=selector 복구 생략, `--provider`/`--model`=LLM 선택. |
| `watch [--every N]` | `poll`을 포그라운드에서 `--every` 분(기본 30)마다 반복, 중단할 때까지. poll의 모든 옵션을 받음. |
| `articles [--topic NAME] [--since DATE] [--until DATE]` | 아카이브 기사(제목·우리 요약·링크)를 나열, 토픽·반열림 `[since, until)` 날짜 범위로 필터 가능. |
| `heal [--dry-run] [--provider P] [--model M]` | selector가 끊긴 crawl 소스를 점검해 LLM으로 복구(라이브 페이지로 검증). `--dry-run`은 제안만 보고 쓰지 않음. |
| `schedule install\|status\|remove [--every N]` | 반복 poll을 OS 스케줄러에 설치·조회·제거(Linux/macOS는 cron, Windows는 schtasks). `--every N`으로 간격 설정. |

## 전송

다이제스트는 이메일, 채팅, 또는 둘 다로 보낼 수 있습니다. 원하는 대상을 하나 이상
설정합니다. 두 채널 모두 newswatcher와 함께 설치되는 동반 패키지가 처리합니다.

- 이메일은 mailmail 패키지로 보냅니다: `--to ADDRESS` 또는 `NEWSWATCHER_DIGEST_TO` 설정
  (mailmail 주소나 주소록 별칭).
- 채팅은 pushpush 패키지로 보냅니다: `--push ROUTE` 또는 `NEWSWATCHER_DIGEST_PUSH` 설정으로,
  pushpush에 미리 설정해 둔 라우트(텔레그램·슬랙·디스코드)를 지정합니다. 다이제스트는
  markdown 메시지 한 통으로 전송됩니다.

`--push`를 쓰기 전에 pushpush 자체 CLI로
라우트만 설정하면 됩니다.

## 뉴스 피드

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

## 설정 파일

newswatcher는 직접 편집하는 설정을 `$XDG_CONFIG_HOME/newswatcher`에 저장합니다.
`XDG_CONFIG_HOME`이 없으면 `~/.config/newswatcher`를 사용합니다. CLI도 같은 파일을
쓰므로 CLI 등록과 직접 편집을 함께 사용할 수 있습니다.

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
(이 삭제는 되돌릴 수 없으니 의도적으로만 켜세요).

## provider 키와 모델

LLM provider 키는 비밀이므로 설정과 분리되어, 같은 설정 디렉터리의
`credentials.json`에 저장합니다. provider의 표준 환경 변수 이름을 키로 쓰는 평범한
JSON 맵입니다.

```json
{
  "GEMINI_API_KEY": "...",
  "OPENAI_API_KEY": "...",
  "CLAUDE_API_KEY": "..."
}
```

각 키는 같은 이름의 환경 변수에서도 읽으며 환경 변수가 우선하므로, 파일을 고치지
않고도 일회성으로 키를 넣을 수 있습니다.

newswatcher는 기본적으로 Gemini 무료 티어로 요약합니다. 다른 provider(그리고 원하면
특정 모델)는 `--provider` / `--model`로 고르거나, `NEWSWATCHER_LLM_PROVIDER` /
`NEWSWATCHER_LLM_MODEL` 설정(`config.toml`의 `llm_provider`, `llm_model`)으로
지속 지정합니다.

```sh
newswatcher poll --provider claude --model claude-sonnet-5
export NEWSWATCHER_LLM_PROVIDER=openai
```

## 책임 있는 수집

모든 피드, 목록 페이지, 기사 요청은 전송 전에 사이트의 robots 정책을 확인하며
newswatcher의 user agent (HTTP 요청에서 프로그램을 식별하는 문자열)를 보냅니다.
허용되지 않은 URL은 요청하지 않습니다. 지속 archive와 발송 다이제스트에는 LLM이 작성한
요약, 원문 링크, 메타데이터만 들어갑니다. 원문 본문은 일시적인 요약 입력으로만 쓰며
archive하거나 발송하지 않습니다.

## 스케줄링

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
사용하므로, LLM 키가 (`credentials.json` 또는 환경 변수로) 닿는지와 `config.toml`에
저장하지 않은 설정이 예약 실행 환경에 제공되는지 확인해야 합니다.

Windows에서는 설치한 사용자의 대화형 세션으로 작업이 등록되므로, 아무도 로그인하지
않은 상태에서는 발화하지 않습니다(화면 잠금은 괜찮지만 로그인 화면은 아닙니다). 또한
작업 스케줄러 기본값에 따라 배터리 전원에서는 시작하지 않습니다. 확인은
`schtasks /Query /TN newswatcher-poll`로 합니다. Linux·macOS의 cron 작업에는 두 제약이
모두 없습니다.

poll은 단일 인스턴스 lock을 잡으므로 예약 poll과 수동 poll이 동시에 돌지 않습니다.
나중에 시작한 쪽은 이미 poll이 실행 중이라고 알리고 종료합니다. lock은 Linux·macOS에서
`flock`, Windows에서 `msvcrt`를 씁니다.

## AI 코딩 에이전트에서 사용

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
