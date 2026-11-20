# r-one-mcp

한국부동산원 **R-ONE 부동산통계**를 AI 채팅(Claude, ChatGPT 등)에서 바로 물어보고 받아 볼 수 있게
해 주는 연결 도구(MCP 서버)입니다.

연결해 두면 "서울 아파트 주간 매매가격지수 최근 추이 보여줘"처럼 말로 물어보는 것만으로 AI가 R-ONE에서
실제 수치를 찾아와 답합니다. 아파트·주택 매매/전세가격지수, 지가지수, 거래현황 등 R-ONE 통계표 700여 개를
다룹니다.

> [hlucent/realestate-stats-mcp](https://github.com/hlucent/realestate-stats-mcp)를 포크해 로컬 실행과 웹(원격) 접속을 모두 지원하도록 재구성했습니다.

## 설치하기 (2단계)

1. **R-ONE 인증키 받기** (무료, 5분) — [방법 보기](#1단계-r-one-인증키-받기)
2. **내가 쓰는 AI에 연결하기** — 아래 표에서 고르세요.

| 내가 쓰는 AI                         | 연결 방법                                                        | 난이도 |
| ------------------------------------ | ---------------------------------------------------------------- | ------ |
| Claude (claude.ai 웹·모바일·Desktop) | [설정 화면에서 주소와 키 입력](#claude-claudeai-웹모바일desktop) | 쉬움   |
| ChatGPT (chatgpt.com)                | [플러그인 화면에서 주소와 키 입력](#chatgpt)                     | 쉬움   |
| Claude Code                          | [명령 한 줄](#claude-code)                                       | 보통   |
| Codex CLI                            | [설정 파일에 몇 줄 추가](#codex-cli)                             | 보통   |
| Gemini CLI                           | [설정 파일에 몇 줄 추가](#gemini-cli)                            | 보통   |
| Cursor · VS Code                     | [설정 파일에 몇 줄 추가](#cursor--vs-code)                       | 보통   |
| Gemini 앱 (gemini.google.com)        | 현재 사용 어려움 ([이유](#gemini-앱))                            | —      |

위 방법은 모두 **공개 서버**(`https://r-one-mcp.vercel.app/mcp`)에 연결하므로 아무것도 설치하지 않습니다.
조회 결과를 내 PC에 CSV 파일로 저장하고 싶다면 [내 PC에서 직접 실행하기](#고급-내-pc에서-직접-실행하기)를 쓰세요.

## 1단계: R-ONE 인증키 받기

인증키는 "내가 R-ONE 데이터를 쓸 수 있는 사람"임을 증명하는 비밀번호 같은 문자열입니다.
무료이며, 따로 회원가입하지 않고 SNS 계정으로 로그인해 받습니다.

1. [R-ONE 인증키 발급 페이지](https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do)에 접속합니다.
   (R-ONE 부동산통계정보시스템 → Open API → 인증키 발급내역)
2. 로그인 화면이 나오면 **네이버·구글·카카오톡** 중 하나로 로그인합니다.
3. 안내에 따라 인증키를 발급받고, 발급된 키(영문·숫자 32자 정도)를 복사해 메모장 등에 둡니다.

알아 둘 점:

- **공공데이터포털(data.go.kr) 키와 다릅니다.** 공공데이터포털 키를 넣으면 `ERROR-290`(인증키가 유효하지 않음) 오류가 납니다.
- 인증키는 **남에게 보여 주지 마세요.** 다른 사람이 내 키로 조회하면 내 하루 사용량이 줄어듭니다.
- 서버는 인증키를 보관하지 않습니다. 각자 자기 키로 조회하므로 다른 사용자와 사용량을 나눠 쓰지 않습니다.

## 2단계: 내가 쓰는 AI에 연결하기

아래에서 `<인증키>`라고 쓴 자리에는 1단계에서 받은 키를 넣습니다. `<`와 `>`는 빼고 키만 넣으세요.

### Claude (claude.ai 웹·모바일·Desktop)

1. [claude.ai](https://claude.ai) 왼쪽 사이드바 → **플러그인** → 사용자 지정 MCP 서버(커넥터) 추가
2. 다음과 같이 입력하고 추가합니다.

   | 칸              | 넣을 값                                                          |
   | --------------- | ---------------------------------------------------------------- |
   | Name            | 아무 이름 (예: `R-ONE 부동산통계`). 목록에 보일 이름일 뿐입니다. |
   | MCP server URL  | `https://r-one-mcp.vercel.app/mcp`                               |
   | Request headers | 이름 `x-api-key`, 값 `<인증키>`                                  |

3. 새 대화에서 "서울 아파트 주간 매매가격지수 최근 4주 보여줘"처럼 물어봅니다.

- 웹에서 한 번 등록하면 같은 계정으로 로그인한 모바일 앱·Claude Desktop·Claude Code에도 자동으로 나타납니다.
- Request headers 칸이 없는 화면이라면 MCP server URL에 키를 붙여 넣어도 됩니다:
  `https://r-one-mcp.vercel.app/mcp?key=<인증키>`

### ChatGPT

ChatGPT는 키를 따로 넣는 칸이 없어서, **주소 끝에 키를 붙이는 방식**으로 연결합니다.
(2026-11 ChatGPT 웹에서 동작 확인)

1. [chatgpt.com](https://chatgpt.com) 왼쪽 메뉴 → **Plugins**
2. 오른쪽 위 **Add** → **Add custom MCP server**
3. 다음과 같이 입력합니다.

   | 칸             | 넣을 값                                         |
   | -------------- | ----------------------------------------------- |
   | Name           | 아무 이름 (예: `R-ONE 부동산통계`)              |
   | Server URL     | `https://r-one-mcp.vercel.app/mcp?key=<인증키>` |
   | Authentication | **No authentication**                           |

4. **I understand and want to continue**에 체크하고 **Create as a plugin**을 누른 뒤, 만들어진 플러그인을 설치합니다.
5. 새 대화 입력창에 `@`를 치고 방금 만든 플러그인을 고른 다음 질문합니다.

- 이 주소 안에 인증키가 들어 있으므로 주소나 설정 화면 스크린샷을 남에게 보내지 마세요.
- ChatGPT가 도구를 쓰기 전에 "허용할까요?"라고 물을 수 있습니다. 허용하면 됩니다.
- ChatGPT 화면 구성은 자주 바뀝니다. 메뉴 이름이 다르면 "custom MCP server"를 추가하는 곳을 찾으세요.

### Claude Code

터미널(명령 프롬프트)에 아래 한 줄을 입력합니다. claude.ai에 이미 커넥터를 등록했다면 이 단계는 필요 없습니다.

```bash
claude mcp add --transport http r-one -s user https://r-one-mcp.vercel.app/mcp --header "x-api-key: <인증키>"
```

### Codex CLI

설정 파일 `config.toml`을 메모장 등으로 열어 맨 아래에 붙여 넣습니다.

- 파일 위치: Windows `C:\Users\<사용자 이름>\.codex\config.toml`, macOS·Linux `~/.codex/config.toml`
- 파일이 없으면 새로 만듭니다.

```toml
[mcp_servers.r-one]
url = "https://r-one-mcp.vercel.app/mcp"
http_headers = { "x-api-key" = "<인증키>" }
```

설정 파일에 키를 직접 적고 싶지 않다면, 키를 환경변수 `R_ONE_API_KEY`에 넣어 두고 아래처럼 씁니다.
이때 Codex를 실행할 때 그 환경변수가 없으면 연결에 실패합니다.

```toml
[mcp_servers.r-one]
url = "https://r-one-mcp.vercel.app/mcp"
bearer_token_env_var = "R_ONE_API_KEY"
```

### Gemini CLI

설정 파일 `settings.json`(Windows `C:\Users\<사용자 이름>\.gemini\settings.json`, macOS·Linux `~/.gemini/settings.json`)에
아래 내용을 넣습니다. 이미 `mcpServers` 항목이 있다면 그 안에 `"r-one": {...}` 부분만 추가합니다.

```json
{
  "mcpServers": {
    "r-one": {
      "httpUrl": "https://r-one-mcp.vercel.app/mcp",
      "headers": { "x-api-key": "<인증키>" }
    }
  }
}
```

### Cursor · VS Code

**Cursor** (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "r-one": {
      "url": "https://r-one-mcp.vercel.app/mcp",
      "headers": { "x-api-key": "<인증키>" }
    }
  }
}
```

**VS Code** (`.vscode/mcp.json` 또는 사용자 설정)

```json
{
  "servers": {
    "r-one": {
      "type": "http",
      "url": "https://r-one-mcp.vercel.app/mcp",
      "headers": { "x-api-key": "<인증키>" }
    }
  }
}
```

### Gemini 앱

Gemini 웹·모바일 앱(gemini.google.com)도 외부 연결 기능이 있지만, 2026-11 현재 미국·유료 요금제·영어
사용자로 제한되어 있고 OAuth 로그인 방식만 지원합니다. 이 서버는 인증키 방식이라 Gemini 앱에서는 쓰기
어렵습니다. Gemini를 쓰고 싶다면 [Gemini CLI](#gemini-cli)를 이용하세요.

## 잘 안 될 때

| 증상                                 | 원인과 해결                                                                                                  |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `ERROR-290` (인증키가 유효하지 않음) | 공공데이터포털 키를 넣었거나 키를 잘못 복사했습니다. R-ONE에서 받은 키인지, 앞뒤에 공백이 없는지 확인하세요. |
| `ERROR-337`                          | 하루 사용량을 다 썼습니다. 다음 날 다시 시도하세요.                                                          |
| 인증키가 없다는 안내가 나옴          | 키 입력 칸(헤더 이름 `x-api-key`)이나 주소 끝 `?key=`가 빠졌습니다.                                          |
| 연결 자체가 안 됨                    | 공개 서버가 잠시 멈췄을 수 있습니다. 아래 안내를 참고하세요.                                                 |

> 공개 서버는 개인이 Vercel 무료 플랜으로 운영하므로 예고 없이 멈추거나 바뀔 수 있습니다.
> 서버가 멈췄을 때는 [내 PC에서 직접 실행하기](#고급-내-pc에서-직접-실행하기)를 쓰세요.

## 제공 도구

R-ONE API는 통계마다 엔드포인트가 따로 있지 않고 통계표코드(STATBL_ID)로 통계를 고르는 구조입니다.
그래서 이 서버도 범용 도구 3개로 모든 통계표를 다룹니다. 사용자는 도구 이름을 몰라도 됩니다. AI가 알아서 고릅니다.

| 도구                                                                               | 용도                                                                                                                                                      |
| ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `search_statistics(keyword, cycle?, limit?)`                                       | 통계표 검색. 통계표명과 조사명·하위 분류(예: 전국주택가격동향조사 > 주간아파트동향)에서 찾음. "주간/월간/분기/연간"은 주기 필터로 처리. 목록은 로컬 캐시  |
| `get_statistics_items(statbl_id, itm_tag?, name_filter?)`                          | 지역(CLS_ID)·항목(ITM_ID)·그룹(GRP_ID) 코드 조회. `name_filter="종로구"`처럼 걸러낼 수 있음                                                               |
| `get_statistics_data(statbl_id, dtacycle_cd, ..., region?, leaf_only?, save_csv?)` | 실제 수치 조회. 값(DTA_VAL)과 단위(UI_NM)를 함께 반환. `region="서울", leaf_only=True`면 서울 25개 구만. `save_csv`를 주면 CSV로 저장하고 미리보기만 반환 |

**통계 해석 주의 (NOTE)**: 표 이름만으로는 알 수 없는 사실은 검색 결과의 `NOTE`, 조회 결과의 `note`로
알려줍니다. 서버 안내문에도 같은 내용이 있습니다. 문구는 `reb_api.TABLE_NOTES`에서 분류 경로별로 관리합니다.

| 분류                                  | 주의                                                                                                                               |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| 전국주택가격동향조사 > 주간아파트동향 | 아파트만 조사합니다. `(주) 매매가격지수`처럼 이름에 "아파트"가 없어도 아파트 지수입니다. 주택종합·연립·단독은 월간동향에 있습니다. |
| 전국주택가격동향조사 > 월간동향       | 주택유형별로 표가 나뉩니다 (이름 끝의 `_아파트`, `_연립다세대`, `_단독주택`, `_주택종합`).                                         |

**CSV 저장** (내 PC에서 직접 실행할 때만): 결과가 커서 대화에 다 넣기 어려울 때 씁니다.
공개 서버에 연결한 경우에는 파일 저장이 동작하지 않습니다.

- 프로젝트 폴더에 저장하려면 절대경로를 넘깁니다 (예: `"D:/projects/분석/data/seoul_weekly.csv"`).
  MCP 서버는 사용자가 어느 프로젝트에서 작업 중인지 알 수 없어서, 작업 폴더를 아는 에이전트가 경로를
  정하도록 했습니다. 서버 안내문과 도구 설명에 이 규칙이 들어 있어 에이전트가 알아서 그렇게 합니다.
- 파일명만 주면 `REB_OUTPUT_DIR`(설정했을 때) 또는 `~/r-one-data` 아래에 저장합니다.
  `"auto"`면 `<STATBL_ID>.csv`.
- 같은 이름이 있으면 덮어쓰지 않고 `_1`, `_2`를 붙입니다. 엑셀에서 바로 열리도록 UTF-8(BOM)으로 씁니다.
- 결과의 `saved_base`로 기준 폴더를 어떻게 정했는지 알 수 있습니다 (`absolute` / `REB_OUTPUT_DIR` / `home`).

**주기코드별 시점 형식**

| 주기 | 코드 | 형식           | 예시   |
| ---- | ---- | -------------- | ------ |
| 년   | YY   | YYYY           | 2024   |
| 반기 | HY   | YYYY0X (X=1,2) | 202301 |
| 분기 | QY   | YYYY0X (X=1~4) | 202301 |
| 월   | MM   | YYYYMM         | 202401 |
| 주   | WK   | YYYYWW         | 202401 |

## 고급: 내 PC에서 직접 실행하기

공개 서버 대신 내 PC에서 서버를 띄우는 방법입니다. 조회 결과를 CSV 파일로 저장하고 싶거나, 공개 서버가
멈췄을 때 씁니다. 이 경우 Claude Code, Claude Desktop, Cursor, VS Code, Codex CLI, Gemini CLI처럼
내 PC에서 돌아가는 AI 프로그램에서만 쓸 수 있습니다.

### 준비

1. [uv](https://docs.astral.sh/uv/) 설치
2. R-ONE 인증키 ([1단계](#1단계-r-one-인증키-받기) 참고)

### 설치

**A. 저장소를 받아서 쓰기** (수정해 가며 쓸 때)

```bash
git clone https://github.com/greenoceanplanet/r-one-mcp
cd r-one-mcp
uv sync
cp .env.example .env   # REB_API_KEY 입력
```

실행 명령: `uv run --directory <저장소 경로> r-one-mcp`

**B. 설치 없이 바로 쓰기** (uvx)

```bash
uvx --from git+https://github.com/greenoceanplanet/r-one-mcp r-one-mcp
```

이 경우 `.env`가 없으므로 키는 클라이언트 설정의 `env`로 넘깁니다.

### API 키 넣는 곳

다음 순서로 찾습니다. 앞에서 찾으면 뒤는 무시합니다.

1. 환경변수 `REB_API_KEY` (MCP 클라이언트 설정의 `env` 항목 포함)
2. 서버를 실행한 폴더의 `.env`
3. 저장소 루트의 `.env` (방법 A)

### 클라이언트별 설정

아래 예시는 방법 A 기준입니다. 방법 B라면 `command`를 `uvx`, `args`를
`["--from", "git+https://github.com/greenoceanplanet/r-one-mcp", "r-one-mcp"]`로
바꾸고 `env`에 키를 넣으세요. `.env`를 쓰면 `env` 항목은 빼도 됩니다.

**Claude Code** (전역 등록)

```bash
claude mcp add r-one-mcp -s user -- uv run --directory /path/to/r-one-mcp r-one-mcp
```

**Claude Desktop / Cursor / Windsurf 등** (`claude_desktop_config.json`, `~/.cursor/mcp.json` 등)

```json
{
  "mcpServers": {
    "r-one-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/r-one-mcp", "r-one-mcp"],
      "env": { "REB_API_KEY": "발급받은키" }
    }
  }
}
```

**VS Code** (`.vscode/mcp.json` 또는 사용자 설정)

```json
{
  "servers": {
    "r-one-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/r-one-mcp", "r-one-mcp"]
    }
  }
}
```

**Codex CLI** (`~/.codex/config.toml`)

```toml
[mcp_servers.r-one-mcp]
command = "uv"
args = ["run", "--directory", "/path/to/r-one-mcp", "r-one-mcp"]
env = { REB_API_KEY = "발급받은키" }
```

**Gemini CLI** (`~/.gemini/settings.json`): Claude Desktop과 같은 `mcpServers` 형식입니다.

### HTTP로 띄우기 (stdio를 지원하지 않는 클라이언트용)

```bash
uv run r-one-mcp --transport http --port 8080
# → http://127.0.0.1:8080/mcp
```

기본 바인드 주소는 `127.0.0.1`입니다. 인증이나 호출 제한이 없으므로 `--host 0.0.0.0`으로
외부에 열 때는 내 키의 일별 트래픽이 소진될 수 있다는 점에 주의하세요.

## 환경변수

| 변수                              | 기본값                                            | 설명                                               |
| --------------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| `REB_API_KEY`                     | (필수)                                            | R-ONE 오픈API 인증키                               |
| `REB_CACHE_DIR`                   | `%LOCALAPPDATA%\r-one-mcp` / `~/.cache/r-one-mcp` | 통계표 목록 캐시 위치                              |
| `REB_CACHE_TTL_DAYS`              | `7`                                               | 통계표 목록 캐시 유효기간(일)                      |
| `REB_OUTPUT_DIR`                  | `~/r-one-data`                                    | `save_csv`에 파일명·상대경로만 줬을 때의 저장 폴더 |
| `MCP_TRANSPORT` / `HOST` / `PORT` | `stdio` / `127.0.0.1` / `8080`                    | 명령줄 옵션 대신 쓸 수 있음                        |

## R-ONE API 실제 동작

원작자 실측(2026-08, DEVLOG.md)과 2026-11-09 재확인 결과입니다.

- 1회 요청 최대 1,000건 (`ERROR-336`), 일별 트래픽 제한 있음 (`ERROR-337`).
- 원작자 실측 당시 `Type=json` 응답은 한글이 깨졌습니다. 2026-11 재확인 때는 정상이었지만,
  검증된 XML 파싱을 그대로 씁니다.
- STATBL_ID 없이 `SttsApiTbl.do`를 부르면 전체 통계표 목록(2026-11 기준 769건)이 나옵니다.
  R-ONE이 배포하는 통계코드 엑셀(665건)은 모두 여기에 포함되고, 나머지 104건은 외부 경제지표(STAT_ID
  `Z000000`)와 상업용부동산 임대동향 일부입니다.
- 목록에는 조사 ID(STAT_ID)만 있고 조사명·분류 경로는 없습니다. 이 서버는 R-ONE 포털의 분류 트리(통계표
  목록 엑셀)로 만든 `catalog.json`(769건 중 717건 경로 확보)을 붙여 검색에 씁니다. 엑셀을 새로 받으면
  `uv run --with pandas --with lxml python scripts/build_catalog.py "All List.xls"`로 다시 만듭니다.
- 목록의 `DATA_END_YY`는 갱신이 늦습니다 (예: 주간 매매가격지수가 2025로 나오지만 2026년 자료가 있음).
- GRP_ID/CLS_ID/ITM_ID는 일부만 채워도 되고, 없는 ID를 넣으면 에러 없이 빈 결과가 나옵니다.
- CLS_ID는 코드 하나만 받고, 상위 지역 코드(예: 서울)를 주면 그 합계 1건만 나옵니다. 그래서 `region`
  옵션은 하위 지역 코드를 찾은 뒤 "코드별 호출"과 "전체 조회 후 걸러내기" 중 R-ONE 호출이 적은 쪽을 고릅니다
  (예: 서울 25개 구 2026년 주간 = 전체 조회 12회, 코드별이면 25회).
- ITM_ID를 비우면 항목이 여러 개인 표는 같은 시점이 항목별로 중복됩니다
  (예: 지가변동률의 `변동률`·`누계`). 응답의 `items`로 섞였는지 확인할 수 있습니다.
- 시작·종료 시점에는 연도만 넣어도 됩니다 (MM 주기에 `START_WRTTIME=2026` → 2026년 1월부터).

## 자주 쓰는 STATBL_ID 예시

| STATBL_ID        | 통계표명                          | 주기 |
| ---------------- | --------------------------------- | ---- |
| A_2024_00178     | (월) 지역별 매매지수_아파트       | MM   |
| A_2024_00180     | (분기) 시군구별 매매지수_아파트   | QY   |
| A_2024_00176     | (월) 지역별 매매지수_공동주택통합 | MM   |
| A_2024_00900     | (연) 지역별 지가지수              | YY   |
| T247493131863202 | (월) 규모별 매매지수_아파트       | MM   |

## 라이선스

MIT. 데이터는 한국부동산원(REB) R-ONE 부동산통계 Open API 제공 공공데이터입니다.
