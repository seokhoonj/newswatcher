# newswatch

newswatch는 RSS 피드와 robots 정책이 허용하는 목록 페이지를 확인하고, 새 기사를
사용자가 정의한 토픽과 매칭한 뒤 LLM으로 요약하여 토픽별 이메일 다이제스트 한 통을
보냅니다.

## 설치

newswatch는 Python 3.11 이상이 필요합니다.

```sh
pip install newswatch
```

## 빠른 시작

토픽과 RSS 소스를 등록하고, 다이제스트 수신 주소와 기본 Gemini LLM provider
(LLM 서비스를 제공하는 업체)용 API 키를 설정한 다음 한 번 poll을 실행합니다.

```sh
newswatch add-topic 보험 --include 보험 재보험 --exclude 스포츠
newswatch add-source 보험뉴스 https://example.com/feed.xml \
  --kind rss --topic 보험
export NEWSWATCH_DIGEST_TO=you@example.com
export GEMINI_API_KEY=your-api-key
newswatch poll
```

`newswatch topics`와 `newswatch sources`로 등록 내용을 확인할 수 있습니다. 전체
명령과 옵션은 `newswatch --help` 또는 `newswatch <command> --help`에서 확인합니다.

## 설정 파일

newswatch는 직접 편집하는 설정을 `$XDG_CONFIG_HOME/newswatch`에 저장합니다.
`XDG_CONFIG_HOME`이 없으면 `~/.config/newswatch`를 사용합니다. CLI도 같은 파일을
쓰므로 CLI 등록과 직접 편집을 함께 사용할 수 있습니다.

`topics.toml`에는 토픽 필터를 작성합니다. 기사 제목이나 피드 요약에 include 키워드가
하나라도 있고 exclude 키워드는 하나도 없을 때 매칭됩니다. `includes`가 비어 있으면
모든 기사가 매칭됩니다.

```toml
[[topic]]
name = "보험"
includes = ["보험", "재보험", "언더라이팅"]
excludes = ["스포츠"]

[[topic]]
name = "규제"
includes = ["금융당국", "지급여력", "자본규제"]
```

`sources.toml`에는 RSS 또는 crawl 소스를 작성합니다. `topics`는 해당 소스에 적용할
토픽 필터를 지정합니다. 소스의 모든 기사를 키워드 필터 없이 보관하려면
`keep_all = true`를 설정합니다.

```toml
[[source]]
name = "보험업계-피드"
kind = "rss"
url = "https://example.com/feed.xml"
topics = ["보험", "규제"]

[[source]]
name = "감독기관-뉴스"
kind = "crawl"
url = "https://example.go.kr/news"
topics = ["규제"]
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
값보다 우선합니다. 예를 들어 `NEWSWATCH_DIGEST_TO`는 `digest_to`에 대응합니다.
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

30분마다 실행하는 cron (정해진 시각에 명령을 실행하는 운영체제 스케줄러) 작업을
설치합니다.

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

스케줄링에는 `crontab` 명령이 필요합니다. 예약 실행도 대화형 poll과 같은 설정을
사용하므로, LLM 키가 (`credentials.json` 또는 환경 변수로) 닿는지와 `config.toml`에
저장하지 않은 설정이 예약 실행 환경에 제공되는지 확인해야 합니다.
