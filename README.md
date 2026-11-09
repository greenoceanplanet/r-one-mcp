# realestate-stats-mcp

한국부동산원 **R-ONE 부동산통계 Open API**를 위한 MCP 서버입니다. 아파트·주택 매매/전세가격지수,
지가지수, 거래현황 등 R-ONE의 통계표 700여 개를 이름으로 찾고 실제 수치를 조회할 수 있습니다.

표준 MCP(stdio / Streamable HTTP)만 쓰기 때문에 Claude Code, Claude Desktop, Cursor, VS Code,
Codex CLI, Gemini CLI 등 MCP를 지원하는 에이전트라면 어디서든 쓸 수 있습니다.

> [hlucent/realestate-stats-mcp](https://github.com/hlucent/realestate-stats-mcp)(fly.io 공개 서버용,
> 2026-08 서비스 종료)를 포크해 로컬 실행용으로 재구성했습니다.

## 제공 도구

R-ONE API는 통계마다 엔드포인트가 따로 있지 않고 통계표코드(STATBL_ID)로 통계를 고르는 구조입니다.
그래서 이 서버도 범용 도구 3개로 모든 통계표를 다룹니다.

| 도구 | 용도 |
|---|---|
| `search_statistics(keyword, cycle?, limit?)` | 통계표 이름 검색. 공백으로 나눈 단어가 모두 들어간 표를 찾음 (예: `"아파트 매매"`). 목록은 로컬 캐시 |
| `get_statistics_items(statbl_id, itm_tag?, name_filter?)` | 지역(CLS_ID)·항목(ITM_ID)·그룹(GRP_ID) 코드 조회. `name_filter="종로구"`처럼 걸러낼 수 있음 |
| `get_statistics_data(statbl_id, dtacycle_cd, ...)` | 실제 수치 조회. 값(DTA_VAL)과 단위(UI_NM)를 함께 반환 |

**주기코드별 시점 형식**

| 주기 | 코드 | 형식 | 예시 |
|---|---|---|---|
| 년 | YY | YYYY | 2024 |
| 반기 | HY | YYYY0X (X=1,2) | 202301 |
| 분기 | QY | YYYY0X (X=1~4) | 202301 |
| 월 | MM | YYYYMM | 202401 |
| 주 | WK | YYYYWW | 202401 |

## 준비

1. [uv](https://docs.astral.sh/uv/) 설치
2. R-ONE 오픈API 인증키 발급:
   https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do
   (공공데이터포털 키와 다릅니다)

## 설치 방법

### A. 저장소를 받아서 쓰기 (수정해 가며 쓸 때)

```bash
git clone https://github.com/greenoceanplanet/realestate-stats-mcp
cd realestate-stats-mcp
uv sync
cp .env.example .env   # REB_API_KEY 입력
```

실행 명령: `uv run --directory <저장소 경로> realestate-stats-mcp`

### B. 설치 없이 바로 쓰기 (uvx)

```bash
uvx --from git+https://github.com/greenoceanplanet/realestate-stats-mcp realestate-stats-mcp
```

이 경우 `.env`가 없으므로 키는 클라이언트 설정의 `env`로 넘깁니다.

## API 키 넣는 곳

다음 순서로 찾습니다. 앞에서 찾으면 뒤는 무시합니다.

1. 환경변수 `REB_API_KEY` (MCP 클라이언트 설정의 `env` 항목 포함)
2. 서버를 실행한 폴더의 `.env`
3. 저장소 루트의 `.env` (방법 A)

## 클라이언트별 설정

아래 예시는 방법 A 기준입니다. 방법 B라면 `command`를 `uvx`, `args`를
`["--from", "git+https://github.com/greenoceanplanet/realestate-stats-mcp", "realestate-stats-mcp"]`로
바꾸고 `env`에 키를 넣으세요. `.env`를 쓰면 `env` 항목은 빼도 됩니다.

**Claude Code** (전역 등록)

```bash
claude mcp add realestate-stats -s user -- uv run --directory /path/to/realestate-stats-mcp realestate-stats-mcp
```

**Claude Desktop / Cursor / Windsurf 등** (`claude_desktop_config.json`, `~/.cursor/mcp.json` 등)

```json
{
  "mcpServers": {
    "realestate-stats": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/realestate-stats-mcp", "realestate-stats-mcp"],
      "env": { "REB_API_KEY": "발급받은키" }
    }
  }
}
```

**VS Code** (`.vscode/mcp.json` 또는 사용자 설정)

```json
{
  "servers": {
    "realestate-stats": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/realestate-stats-mcp", "realestate-stats-mcp"]
    }
  }
}
```

**Codex CLI** (`~/.codex/config.toml`)

```toml
[mcp_servers.realestate-stats]
command = "uv"
args = ["run", "--directory", "/path/to/realestate-stats-mcp", "realestate-stats-mcp"]
```

**Gemini CLI** (`~/.gemini/settings.json`): Claude Desktop과 같은 `mcpServers` 형식입니다.

### HTTP로 띄우기 (stdio를 지원하지 않는 클라이언트용)

```bash
uv run realestate-stats-mcp --transport http --port 8080
# → http://127.0.0.1:8080/mcp
```

기본 바인드 주소는 `127.0.0.1`입니다. 인증이나 호출 제한이 없으므로 `--host 0.0.0.0`으로
외부에 열 때는 내 키의 일별 트래픽이 소진될 수 있다는 점에 주의하세요.

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `REB_API_KEY` | (필수) | R-ONE 오픈API 인증키 |
| `REB_CACHE_DIR` | `%LOCALAPPDATA%\realestate-stats-mcp` / `~/.cache/realestate-stats-mcp` | 통계표 목록 캐시 위치 |
| `REB_CACHE_TTL_DAYS` | `7` | 통계표 목록 캐시 유효기간(일) |
| `MCP_TRANSPORT` / `HOST` / `PORT` | `stdio` / `127.0.0.1` / `8080` | 명령줄 옵션 대신 쓸 수 있음 |

## R-ONE API 실제 동작 (원작자 실측, DEVLOG.md 참고)

- 1회 요청 최대 1,000건 (`ERROR-336`), 일별 트래픽 제한 있음 (`ERROR-337`)
- `Type=json` 응답은 한글이 깨지는 서버 버그가 있어 항상 XML로 받아 파싱합니다.
- STATBL_ID 없이 `SttsApiTbl.do`를 부르면 전체 통계표 목록이 나옵니다. 이 서버는 이를 디스크에
  캐시하고 이름 검색에 씁니다.
- GRP_ID/CLS_ID/ITM_ID는 일부만 채워도 되고, 없는 ID를 넣으면 에러 없이 빈 결과가 나옵니다.

## 자주 쓰는 STATBL_ID 예시

| STATBL_ID | 통계표명 | 주기 |
|---|---|---|
| A_2024_00178 | (월) 지역별 매매지수_아파트 | MM |
| A_2024_00180 | (분기) 시군구별 매매지수_아파트 | QY |
| A_2024_00176 | (월) 지역별 매매지수_공동주택통합 | MM |
| A_2024_00900 | (연) 지역별 지가지수 | YY |
| T247493131863202 | (월) 규모별 매매지수_아파트 | MM |

## 라이선스

MIT. 데이터는 한국부동산원(REB) R-ONE 부동산통계 Open API 제공 공공데이터입니다.
