> ⚠️ **서비스 종료 안내**
> 본 MCP 서버는 2026-08-23부로 fly.io 배포를 종료했습니다.
> 코드는 개발 참고용으로 저장소에 남겨둡니다.

# realestate-stats-mcp

한국부동산원(R-ONE) 부동산통계 Open API를 위한 MCP 서버. 아파트 매매/전세가격지수, 지가변동률,
부동산 거래현황 등 R-ONE이 제공하는 수백 개 통계표를 이름으로 검색하고 실제 수치를 조회할 수 있는
**범용 통계조회 도구**입니다.

> 이 API는 통계마다 별도 엔드포인트가 있는 게 아니라, 통계표코드(STATBL_ID)로 원하는 통계를 지정해
> 조회하는 구조입니다. 그래서 이 MCP도 통계별 전용 툴이 아니라 3개의 범용 툴로 모든 통계표를
> 다룹니다.

## 제공 도구 (Tools)

### `search_statistics(keyword)`
통계표를 이름/키워드로 검색합니다. 예: "아파트 매매", "지가변동률", "실거래가"
→ STATBL_ID, 통계표명, 주기, 데이터 존재 기간을 반환합니다.

### `get_statistics_items(statbl_id, itm_tag=None)`
특정 통계표의 지역/분류/그룹 코드를 조회합니다. 실제 데이터를 조회하기 전에 지역 코드(CLS_ID)
등을 알아내는 용도입니다.

### `get_statistics_data(statbl_id, dtacycle_cd, start_wrttime=None, end_wrttime=None, cls_id=None, grp_id=None, itm_id=None)`
실제 통계 수치를 조회합니다. 단위(UI_NM)와 함께 값을 반환합니다.

**주기코드(DTACYCLE_CD)별 시점 형식**

| 주기 | 코드 | 형식 | 예시 |
|---|---|---|---|
| 년 | YY | YYYY | 2024 |
| 반기 | HY | YYYY0X (X=1,2) | 202301 |
| 분기 | QY | YYYY0X (X=1~4) | 202301 |
| 월 | MM | YYYYMM | 202401 |
| 주 | WK | YYYYWW | 202401 |

## 설치 및 실행

```bash
pip install -r requirements.txt
cp .env.example .env
# .env에 REB_API_KEY 입력 (R-ONE 사이트에서 직접 발급 — 공공데이터포털 키와 다를 수 있음)
python server.py
```

## 환경변수

| 변수명 | 설명 |
|---|---|
| `REB_API_KEY` | 한국부동산원 R-ONE 오픈API 인증키 (`https://www.reb.or.kr/r-one/portal/openapi/openApiActKeyPage.do` 에서 발급) |

## 배포 (fly.io)

```bash
fly launch --no-deploy
fly secrets set REB_API_KEY=발급받은키
flyctl deploy
```

배포 후 Claude.ai 커넥터 연결 시 주소 끝에 `/mcp`를 붙여서 연결하세요.
예: `https://realestate-stats-mcp.fly.dev/mcp`

## 실제 동작 기준 제약사항 (2026-08-16 실측 완료 — DEVLOG.md 참고)

- 1회 요청 최대 1,000건 (`ERROR-336`)
- 일별 트래픽 제한 있음 (`ERROR-337`, 초과 시 익일까지 대기)
- **`Type=json` 응답은 서버 인코딩 버그로 한글이 깨진다.** 이 MCP는 이 문제를 피하기 위해
  항상 기본(XML) 응답을 사용하고 내부에서 XML을 파싱한다. (직접 API를 호출할 경우 참고)
- STATBL_ID 없이 `SttsApiTbl.do` 호출 시 전체 통계표 목록(738건, 실측 시점 기준)이 정상
  반환된다. 이 MCP는 이를 최초 1회 호출해 인메모리로 캐시하고, `search_statistics`는
  STATBL_NM 문자열 매칭으로 필터링한다. (캐시는 서버 프로세스 생명주기 동안만 유지 — 재시작 시 리셋)
- 선택 파라미터(GRP_ID/CLS_ID/ITM_ID)를 일부만 채워도 500 에러는 재현되지 않는다. 존재하지
  않는 ID를 넣으면 에러가 아니라 `INFO-200`(데이터 없음, 빈 결과)으로 정상 응답한다.
- 응답 루트 구조가 두 가지다: 정상/빈 결과는 `<엔드포인트명><head><RESULT>...`, 에러(예:
  `ERROR-300`)는 `<head>` 없이 루트가 바로 `<RESULT>`. `reb_api.py`가 두 형태를 모두 처리한다.

## "거래/매매/가격" 관련 STATBL_ID 후보 (2026-08-16 실측 확보, 340건 중 일부)

| STATBL_ID | STATBL_NM | 주기 | 자료기간 |
|---|---|---|---|
| A_2024_00178 | (월) 지역별 매매지수_아파트 | MM | 2006~2024 |
| A_2024_00180 | (분기) 시군구별 매매지수_아파트 | QY | 2006~2024 |
| A_2024_00176 | (월) 지역별 매매지수_공동주택통합 | MM | 2006~2024 |
| A_2024_00900 | (연) 지역별 지가지수 | YY | 1987~2025 |
| A_2024_00175 | 지역별 거래동향(구) | MM | 2010~2015 |
| A_2024_00162 | 지역별 월세가격지수(구) | MM | 2010~2015 |
| T247493131863202 | (월) 규모별 매매지수_아파트 | MM | 2006~2024 |

전체 후보는 `search_statistics("매매")`, `search_statistics("거래")`, `search_statistics("가격")`
등으로 직접 조회 가능(각 100건 이상). 위 표는 대표적인 항목만 발췌한 것.

## 라이선스

한국부동산원 제공 공공데이터, 이용허락범위 제한 없음(공공데이터포털 명시 기준).

## 데이터 출처

한국부동산원(REB) R-ONE 부동산통계 Open API — `https://www.reb.or.kr/r-one/openapi`
