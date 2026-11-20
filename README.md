# r-one-mcp

한국부동산원 **R-ONE 부동산통계**를 AI 채팅(Claude, ChatGPT 등)에서 물어볼 수 있게 해 주는 MCP 서버입니다.
"서울 아파트 주간 매매가격지수 최근 추이 보여줘"처럼 물으면 AI가 R-ONE에서 실제 수치를 찾아와 답합니다.
아파트·주택 매매/전세가격지수, 지가지수, 거래현황 등 R-ONE 통계표 700여 개를 다룹니다.

> [hlucent/realestate-stats-mcp](https://github.com/hlucent/realestate-stats-mcp)를 포크해 로컬 실행과 웹(원격) 접속을 모두 지원하도록 재구성했습니다.

## 1. 인증키 받기

[R-ONE 인증키 발급 페이지](https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do)에서
네이버·구글·카카오 계정으로 로그인해 무료로 받습니다.

- **공공데이터포털(data.go.kr) 키와 다릅니다.** 공공데이터포털 키를 넣으면 `ERROR-290`이 납니다.
- 키는 남에게 보여 주지 마세요. 서버는 키를 보관하지 않고, 각자 자기 키로 조회합니다.

## 2. 연결하기

공개 서버에 연결하므로 설치할 것은 없습니다. 어느 AI 프로그램이든 아래 두 가지만 넣으면 됩니다.

| 항목      | 값                                                                  |
| --------- | ------------------------------------------------------------------- |
| 서버 주소 | `https://r-one-mcp.vercel.app/mcp`                                  |
| 인증키    | 헤더 `x-api-key: <인증키>` (헤더를 못 넣는 곳은 주소 끝에 `?key=<인증키>`) |

**claude.ai** (웹·모바일·Desktop): 왼쪽 사이드바 → **플러그인** → 사용자 지정 MCP 서버 추가 →
URL에 서버 주소, Request headers에 `x-api-key` = `<인증키>`.
한 번 등록하면 같은 계정의 모바일 앱·Claude Desktop·Claude Code에도 나타납니다.

**ChatGPT**: 왼쪽 메뉴 **Plugins** → **Add** → **Add custom MCP server** →
Server URL에 `https://r-one-mcp.vercel.app/mcp?key=<인증키>`, Authentication은 **No authentication**.
만든 플러그인을 설치한 뒤 대화창에서 `@`로 골라 씁니다. (2026-11 동작 확인)

**터미널 프로그램**

```bash
# Claude Code
claude mcp add --transport http r-one -s user https://r-one-mcp.vercel.app/mcp --header "x-api-key: <인증키>"

# Codex CLI (키를 환경변수에 두고 이름만 등록. Windows는 setx 후 터미널을 새로 열기)
setx R_ONE_API_KEY "<인증키>"
codex mcp add r-one --url https://r-one-mcp.vercel.app/mcp --bearer-token-env-var R_ONE_API_KEY

# Antigravity CLI (옛 Gemini CLI). -H는 서버 이름보다 앞에
agy mcp add -H "x-api-key: <인증키>" r-one https://r-one-mcp.vercel.app/mcp
```

Cursor·VS Code 등은 각 프로그램의 MCP 설정에 위 서버 주소와 헤더를 넣으면 됩니다.

> 키를 AI 대화창에 붙여 넣지 마세요. 대화 기록에 남습니다. 설정 화면이나 명령에 직접 넣으세요.

## 잘 안 될 때

- `ERROR-290`: R-ONE에서 받은 키가 맞는지, 앞뒤 공백이 없는지 확인
- `ERROR-337`: 하루 사용량 초과. 다음 날 다시 시도
- 연결 자체가 안 됨: 공개 서버는 개인이 Vercel 무료 플랜으로 운영하므로 멈출 수 있습니다.
  이때는 [내 PC에서 직접 실행하기](#내-pc에서-직접-실행하기)를 쓰세요.

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

## 내 PC에서 직접 실행하기

공개 서버가 멈췄거나 조회 결과를 CSV 파일로 저장하고 싶을 때 씁니다. [uv](https://docs.astral.sh/uv/)가 필요합니다.

```bash
git clone https://github.com/greenoceanplanet/r-one-mcp
cd r-one-mcp
uv sync
cp .env.example .env   # REB_API_KEY 입력
```

인증키는 환경변수 `REB_API_KEY` → 실행 폴더의 `.env` → 저장소 루트의 `.env` 순으로 찾습니다.

**Claude Code**

```bash
claude mcp add r-one-mcp -s user -- uv run --directory /path/to/r-one-mcp r-one-mcp
```

**Claude Desktop·Cursor 등** (`mcpServers` 형식. Codex·VS Code도 같은 command/args를 각자 형식으로 넣으면 됩니다)

```json
{
  "mcpServers": {
    "r-one-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/r-one-mcp", "r-one-mcp"]
    }
  }
}
```

저장소를 받지 않고 `uvx --from git+https://github.com/greenoceanplanet/r-one-mcp r-one-mcp`로 실행할 수도
있습니다. 이때는 `.env`가 없으므로 설정의 `env`에 `REB_API_KEY`를 넣습니다.

HTTP로 띄우려면 `uv run r-one-mcp --transport http --port 8080`(→ `http://127.0.0.1:8080/mcp`).
인증·호출 제한이 없으므로 `--host 0.0.0.0`으로 외부에 열면 내 키의 사용량이 소진될 수 있습니다.

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
