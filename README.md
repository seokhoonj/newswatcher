# newswatch

**한국어** | [English](README.en.md)

newswatch는 RSS 피드와 robots 정책이 허용하는 목록 페이지를 확인하고, 새 기사를
사용자가 정의한 토픽과 매칭한 뒤 LLM으로 요약하여 토픽별 다이제스트 한 통을 이메일이나
채팅으로 보냅니다. 같은 사건을 여러 매체가 보도하면 한 항목으로 묶습니다. 토픽은 직접
정의하므로 같은 도구로 종목, 기술, 정책, 그 밖에 피드가 다루는 어떤 주제든 추적할 수
있습니다.

## 설치

newswatch는 Python 3.11 이상이 필요합니다.

```sh
pip install newswatch
```

## 빠른 시작

토픽과 RSS 소스를 등록하고, 다이제스트 수신 주소와 기본 Gemini LLM provider
(LLM 서비스를 제공하는 업체)용 API 키를 설정한 다음 한 번 poll을 실행합니다.

```sh
newswatch add-topic 증시 --include 코스피 금리 실적 반도체 --exclude 연예
newswatch add-source 한국경제 https://www.hankyung.com/feed/all-news \
  --kind rss --topic 증시
export NEWSWATCH_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatch poll
```

토픽은 피드의 언어로 매칭하므로 키워드도 피드 언어에 맞춥니다. 한국어 피드에는 한국어
키워드를, 영어 피드에는 영어 키워드를 씁니다.

`newswatch topics`와 `newswatch sources`로 등록 내용을 확인할 수 있습니다. 전체
명령과 옵션은 `newswatch --help` 또는 `newswatch <command> --help`에서 확인합니다.

## 명령

전체 옵션은 `newswatch --help` 또는 `newswatch <command> --help`에서 확인하고,
`newswatch --version`은 버전을 출력합니다.

- `add-topic <name> [--include WORD...] [--exclude WORD...]` / `topics` — 토픽 필터를 정의하고 나열합니다.
- `add-source <name> <url> [--kind rss|crawl] [--topic NAME]... [--keep-all]` / `sources` — 소스를 등록하고 나열합니다. crawl 소스는 selector도 받습니다: `--item --title --link`(필수), `--date --body-selector`(선택). `--keep-all`은 키워드 필터 없이 모든 기사를 보관합니다.
- `recent <url> [--limit N]` — 등록 전에 피드의 최신 항목을 저장 없이 미리 봅니다.
- `poll` / `watch [--every N]` — 수집 → 요약 → 발송을 한 번 수행하거나 주기적으로 포그라운드에서 반복합니다. 둘 다 `--to ADDRESS`(이메일 수신자), `--push ROUTE`(pushpush 채팅 라우트), `--no-mail`, `--no-store`, `--no-heal`, LLM `--provider` / `--model`을 받습니다.
- `articles [--topic NAME] [--since DATE] [--until DATE]` — archive된 기사를 나열합니다.
- `heal [--dry-run] [--provider P] [--model M]` — 매칭이 끊긴 crawl selector를 점검하고 복구합니다.
- `schedule install|status|remove [--every N]` — 반복 poll을 운영체제 스케줄러에 등록합니다.

## 배달

다이제스트는 이메일, 채팅, 또는 둘 다로 보낼 수 있습니다. 원하는 대상을 하나 이상
설정합니다.

- 이메일은 mailmail로 보냅니다: `--to ADDRESS` 또는 `NEWSWATCH_DIGEST_TO` 설정
  (mailmail 주소나 주소록 별칭).
- 채팅은 pushpush로 보냅니다: `--push ROUTE` 또는 `NEWSWATCH_DIGEST_PUSH` 설정으로,
  pushpush에 미리 설정해 둔 라우트(텔레그램·슬랙·디스코드)를 지정합니다. 다이제스트는
  markdown 메시지 한 통으로 전송됩니다.

두 패키지는 newswatch와 함께 설치되므로, `--push`를 쓰기 전에 pushpush 자체 CLI로
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

## 설정 파일

newswatch는 직접 편집하는 설정을 `$XDG_CONFIG_HOME/newswatch`에 저장합니다.
`XDG_CONFIG_HOME`이 없으면 `~/.config/newswatch`를 사용합니다. CLI도 같은 파일을
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
값보다 우선합니다. 예를 들어 `NEWSWATCH_DIGEST_TO`는 `digest_to`에, `NEWSWATCH_DIGEST_PUSH`는
`digest_push`에 대응합니다.
기사 archive (지속적으로 보관하는 기록)와 실행 상태는 XDG data/state 디렉터리를
사용하며, `NEWSWATCH_DATA_DIR`와 `NEWSWATCH_STATE_DIR`로 위치를 바꿀 수 있습니다.

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

newswatch는 기본적으로 Gemini 무료 티어로 요약합니다. 다른 provider(그리고 원하면
특정 모델)는 `--provider` / `--model`로 고르거나, `NEWSWATCH_LLM_PROVIDER` /
`NEWSWATCH_LLM_MODEL` 설정(`config.toml`의 `llm_provider`, `llm_model`)으로
지속 지정합니다.

```sh
newswatch poll --provider claude --model claude-sonnet-5
export NEWSWATCH_LLM_PROVIDER=openai
```

## 책임 있는 수집

모든 피드, 목록 페이지, 기사 요청은 전송 전에 사이트의 robots 정책을 확인하며
newswatch의 user agent (HTTP 요청에서 프로그램을 식별하는 문자열)를 보냅니다.
허용되지 않은 URL은 요청하지 않습니다. 지속 archive와 발송 이메일에는 LLM이 작성한
요약, 원문 링크, 메타데이터만 들어갑니다. 원문 본문은 일시적인 요약 입력으로만 쓰며
archive하거나 이메일로 보내지 않습니다.

## 스케줄링

30분마다 실행하는 반복 poll을 운영체제 스케줄러(정해진 시각에 명령을 실행하는
OS 기능)에 설치합니다.

```sh
newswatch schedule install
```

분, `Nm`, `Nh` 형식으로 다른 주기를 지정할 수 있으며 작업 상태 확인과 삭제도
지원합니다.

```sh
newswatch schedule install --every 2h
newswatch schedule status
newswatch schedule remove
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
`schtasks /Query /TN newswatch-poll`로 합니다. Linux·macOS의 cron 작업에는 두 제약이
모두 없습니다.

poll은 단일 인스턴스 lock을 잡으므로 예약 poll과 수동 poll이 동시에 돌지 않습니다.
나중에 시작한 쪽은 이미 poll이 실행 중이라고 알리고 종료합니다. lock은 Linux·macOS에서
`flock`, Windows에서 `msvcrt`를 씁니다.
