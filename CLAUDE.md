# CLAUDE.md — r-one-mcp

한국부동산원 R-ONE 부동산통계 Open API용 MCP 서버. 특정 클라이언트에 묶이지 않는 로컬 실행용.

## 구조

- `src/r_one_mcp/reb_api.py` — R-ONE API 클라이언트 (MCP 의존 없음)
- `src/r_one_mcp/server.py` — FastMCP 툴 3개 + `main()` (stdio 기본, `--transport http` 선택)
- `src/r_one_mcp/catalog.json` — 통계표ID → R-ONE 분류 경로 (`scripts/build_catalog.py`로 생성)
- 실행: `uv run r-one-mcp`
- `DEVPLAN.md`, `DEVLOG.md` — 원작자의 API 실측 기록 (fly.io 배포 관련 내용은 더 이상 해당 없음)

## 원칙

- 툴은 범용 3개(`search_statistics`, `get_statistics_items`, `get_statistics_data`)만 둔다.
  통계표별 전용 툴을 만들지 않는다.
- 클라이언트 전용 기능(특정 에이전트만 아는 확장)은 쓰지 않는다. 표준 MCP 툴/설명만 사용.
- stdio 모드에서는 stdout에 아무것도 출력하지 않는다 (프로토콜이 깨진다). 로그는 stderr로.
- API 응답은 항상 XML로 받는다 (`Type=json`은 한글이 깨지는 서버 버그).

## API 키

- `REB_API_KEY`는 환경변수 → cwd `.env` → 저장소 루트 `.env` 순으로 찾는다. 하드코딩 금지.
- 키를 출력할 때는 앞 4자리 + 길이만 마스킹해서 보인다.
- `.env`는 UTF-8(BOM 없음)으로 저장한다.
- 인증 에러(`ERROR-290`)가 나면 공공데이터포털 키가 아니라 R-ONE에서 발급한 키인지부터 확인.

## 환경 주의

- 저장소 경로에 한글이 있으면 Python 3.12 이하에서 editable 설치의 `.pth` 디코딩 오류가 난다
  (시스템 로캘이 cp949/cp1252일 때). 그래서 `.python-version`을 3.13으로 둔다.
