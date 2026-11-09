# r-one-mcp

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
| `search_statistics(keyword, cycle?, limit?)` | 통계표 검색. 통계표명과 조사명·하위 분류(예: 전국주택가격동향조사 > 주간아파트동향)에서 찾음. "주간/월간/분기/연간"은 주기 필터로 처리. 목록은 로컬 캐시 |
| `get_statistics_items(statbl_id, itm_tag?, name_filter?)` | 지역(CLS_ID)·항목(ITM_ID)·그룹(GRP_ID) 코드 조회. `name_filter="종로구"`처럼 걸러낼 수 있음 |
| `get_statistics_data(statbl_id, dtacycle_cd, ..., save_csv?)` | 실제 수치 조회. 값(DTA_VAL)과 단위(UI_NM)를 함께 반환. `save_csv`를 주면 CSV로 저장하고 미리보기만 반환 |

**CSV 저장**: 결과가 커서 대화에 다 넣기 어려울 때 씁니다.

- 프로젝트 폴더에 저장하려면 절대경로를 넘깁니다 (예: `"D:/projects/분석/data/seoul_weekly.csv"`).
  MCP 서버는 사용자가 어느 프로젝트에서 작업 중인지 알 수 없어서, 작업 폴더를 아는 에이전트가 경로를
  정하도록 했습니다. 서버 안내문과 도구 설명에 이 규칙이 들어 있어 에이전트가 알아서 그렇게 합니다.
- 파일명만 주면 `REB_OUTPUT_DIR`(설정했을 때) 또는 `~/r-one-data` 아래에 저장합니다.
  `"auto"`면 `<STATBL_ID>.csv`.
- 같은 이름이 있으면 덮어쓰지 않고 `_1`, `_2`를 붙입니다. 엑셀에서 바로 열리도록 UTF-8(BOM)으로 씁니다.
- 결과의 `saved_base`로 기준 폴더를 어떻게 정했는지 알 수 있습니다 (`absolute` / `REB_OUTPUT_DIR` / `home`).

**통계 해석 주의 (NOTE)**: 표 이름만으로는 알 수 없는 사실은 검색 결과의 `NOTE`, 조회 결과의 `note`로
알려줍니다. 서버 안내문에도 같은 내용이 있습니다. 문구는 `reb_api.TABLE_NOTES`에서 분류 경로별로 관리합니다.

| 분류 | 주의 |
|---|---|
| 전국주택가격동향조사 > 주간아파트동향 | 아파트만 조사합니다. `(주) 매매가격지수`처럼 이름에 "아파트"가 없어도 아파트 지수입니다. 주택종합·연립·단독은 월간동향에 있습니다. |
| 전국주택가격동향조사 > 월간동향 | 주택유형별로 표가 나뉩니다 (이름 끝의 `_아파트`, `_연립다세대`, `_단독주택`, `_주택종합`). |

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
git clone https://github.com/greenoceanplanet/r-one-mcp
cd r-one-mcp
uv sync
cp .env.example .env   # REB_API_KEY 입력
```

실행 명령: `uv run --directory <저장소 경로> r-one-mcp`

### B. 설치 없이 바로 쓰기 (uvx)

```bash
uvx --from git+https://github.com/greenoceanplanet/r-one-mcp r-one-mcp
```

이 경우 `.env`가 없으므로 키는 클라이언트 설정의 `env`로 넘깁니다.

## API 키 넣는 곳

다음 순서로 찾습니다. 앞에서 찾으면 뒤는 무시합니다.

1. 환경변수 `REB_API_KEY` (MCP 클라이언트 설정의 `env` 항목 포함)
2. 서버를 실행한 폴더의 `.env`
3. 저장소 루트의 `.env` (방법 A)

## 클라이언트별 설정

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

| 변수 | 기본값 | 설명 |
|---|---|---|
| `REB_API_KEY` | (필수) | R-ONE 오픈API 인증키 |
| `REB_CACHE_DIR` | `%LOCALAPPDATA%\r-one-mcp` / `~/.cache/r-one-mcp` | 통계표 목록 캐시 위치 |
| `REB_CACHE_TTL_DAYS` | `7` | 통계표 목록 캐시 유효기간(일) |
| `REB_OUTPUT_DIR` | `~/r-one-data` | `save_csv`에 파일명·상대경로만 줬을 때의 저장 폴더 |
| `MCP_TRANSPORT` / `HOST` / `PORT` | `stdio` / `127.0.0.1` / `8080` | 명령줄 옵션 대신 쓸 수 있음 |

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
- ITM_ID를 비우면 항목이 여러 개인 표는 같은 시점이 항목별로 중복됩니다
  (예: 지가변동률의 `변동률`·`누계`). 응답의 `items`로 섞였는지 확인할 수 있습니다.
- 시작·종료 시점에는 연도만 넣어도 됩니다 (MM 주기에 `START_WRTTIME=2026` → 2026년 1월부터).

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
