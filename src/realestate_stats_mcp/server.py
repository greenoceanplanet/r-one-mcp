"""realestate-stats-mcp — 한국부동산원(R-ONE) 부동산통계 범용 조회 MCP 서버.

특정 클라이언트에 묶이지 않도록 표준 MCP만 사용한다.
- 기본: stdio (Claude Code/Desktop, Cursor, Codex, Gemini CLI, VS Code 등 대부분의 에이전트)
- 선택: --transport http (Streamable HTTP만 지원하는 클라이언트·원격 접속용)

R-ONE API는 통계표코드(STATBL_ID)로 통계를 고르는 구조라, 통계표별 툴을 만들지 않고
3개의 범용 툴로 모든 통계표를 다룬다.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from . import __version__, reb_api

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_env() -> None:
    """환경변수가 우선. 없으면 현재 폴더 → 프로젝트 루트의 .env 순으로 읽는다.

    클라이언트마다 서버를 띄우는 작업 폴더가 달라서 cwd의 .env만 믿으면 키를 못 찾는다.
    """
    for candidate in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False, encoding="utf-8-sig")


INSTRUCTIONS = """\
한국부동산원 R-ONE 부동산통계(아파트·주택 매매/전세가격지수, 지가지수·지가변동률, 거래현황,
월세, 상업용부동산 임대동향 등)를 조회한다.

사용 순서:
1. search_statistics(keyword) 로 통계표를 찾아 STATBL_ID와 주기(DTACYCLE_CD)를 확인한다.
2. 특정 지역·항목만 필요하면 get_statistics_items(statbl_id) 로 CLS_ID(주로 지역)·ITM_ID·GRP_ID를 찾는다.
3. get_statistics_data(...) 로 실제 수치를 조회한다. 결과 값(DTA_VAL)은 단위(UI_NM)와 함께 제시한다.

주의: R-ONE API는 일별 트래픽 제한이 있으므로 기간·지역을 좁혀서 조회한다.
"""

mcp = FastMCP("realestate-stats", instructions=INSTRUCTIONS, version=__version__)


def _pick(row: dict, fields: tuple[str, ...]) -> dict:
    return {f: row.get(f) for f in fields}


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except reb_api.RebApiError as e:
        raise ToolError(f"[{e.code}] {e.message}") from e


TABLE_FIELDS = ("STATBL_ID", "STATBL_NM", "DTACYCLE_CD", "DTACYCLE_NM",
                "DATA_START_YY", "DATA_END_YY", "RPSTUI_NM")
ITEM_FIELDS = ("ITM_TAG", "ITM_ID", "PAR_ITM_ID", "ITM_NM", "ITM_FULLNM", "UI_NM")
DATA_FIELDS = ("WRTTIME_IDTFR_ID", "WRTTIME_DESC", "CLS_ID", "CLS_NM", "CLS_FULLNM",
               "GRP_NM", "ITM_NM", "ITM_FULLNM", "DTA_VAL", "UI_NM")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def search_statistics(keyword: str, cycle: str | None = None, limit: int = 50) -> dict:
    """R-ONE 통계표를 이름으로 검색한다.

    키워드를 공백으로 나눈 모든 단어가 통계표명에 들어간 항목을 찾는다 (순서·띄어쓰기 무관).
    예: "아파트 매매", "전세 지수", "지가", "거래". 빈 문자열이면 전체 목록.
    통계표 목록은 로컬에 캐시되므로(기본 7일) 반복 검색해도 API 트래픽을 쓰지 않는다.

    Args:
        keyword: 통계표명 검색어
        cycle: 주기 필터. YY(년)/HY(반기)/QY(분기)/MM(월)/WK(주) 중 하나 (옵션)
        limit: 최대 반환 건수 (기본 50)

    Returns:
        total: 검색된 전체 건수, count: 반환 건수,
        results: [{STATBL_ID, STATBL_NM, DTACYCLE_CD(쉼표로 여러 주기 가능), DTACYCLE_NM,
                   DATA_START_YY, DATA_END_YY, RPSTUI_NM}]
    """
    rows = _run(reb_api.search_statistics_tables, keyword, cycle)
    limit = max(1, limit)
    return {
        "total": len(rows),
        "count": min(len(rows), limit),
        "results": [_pick(r, TABLE_FIELDS) for r in rows[:limit]],
    }


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def get_statistics_items(statbl_id: str, itm_tag: str | None = None,
                         name_filter: str | None = None) -> dict:
    """통계표의 그룹/분류/항목 코드를 조회한다.

    get_statistics_data에 넘길 CLS_ID(주로 지역)·ITM_ID·GRP_ID를 찾는 용도다.
    예: "종로구"의 CLS_ID를 여기서 확인한 뒤 get_statistics_data(cls_id=...)로 넘긴다.

    Args:
        statbl_id: 통계표ID (search_statistics 결과)
        itm_tag: "그룹" / "분류" / "항목" 중 하나로 걸러냄 (옵션)
        name_filter: ITM_FULLNM에 이 문자열이 들어간 것만 반환 (옵션, 예: "서울", "종로구")

    Returns:
        count, results: [{ITM_TAG, ITM_ID, PAR_ITM_ID, ITM_NM, ITM_FULLNM(예: "서울>종로구"), UI_NM}]
    """
    rows = _run(reb_api.get_statistics_items, statbl_id, itm_tag)
    if name_filter:
        key = name_filter.replace(" ", "")
        rows = [r for r in rows if key in (r.get("ITM_FULLNM") or r.get("ITM_NM") or "").replace(" ", "")]
    return {"count": len(rows), "results": [_pick(r, ITEM_FIELDS) for r in rows]}


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def get_statistics_data(
    statbl_id: str,
    dtacycle_cd: str,
    start_wrttime: str | None = None,
    end_wrttime: str | None = None,
    wrttime_idtfr_id: str | None = None,
    grp_id: str | None = None,
    cls_id: str | None = None,
    itm_id: str | None = None,
    max_rows: int = 1000,
) -> dict:
    """통계표의 실제 수치를 조회한다.

    시점 형식은 주기코드(dtacycle_cd)에 따라 다르다 (start/end/wrttime_idtfr_id 공통):
        YY(년)   YYYY            예: 2024
        HY(반기) YYYY0X (X=1,2)  예: 202301
        QY(분기) YYYY0X (X=1~4)  예: 202304
        MM(월)   YYYYMM          예: 202412
        WK(주)   YYYYWW          예: 202452

    grp_id/cls_id/itm_id는 get_statistics_items로 확인한다. 일부만 채워도 된다.
    존재하지 않는 코드를 넣으면 에러 없이 빈 결과(count=0)가 나온다.

    Args:
        statbl_id: 통계표ID (필수)
        dtacycle_cd: 주기코드 YY/HY/QY/MM/WK (필수)
        start_wrttime / end_wrttime: 조회 기간 (옵션)
        wrttime_idtfr_id: 특정 시점 하나만 조회 (옵션)
        grp_id / cls_id / itm_id: 그룹 / 분류(주로 지역) / 항목 필터 (옵션)
        max_rows: 최대 반환 건수 (기본 1000). truncated=true면 조건을 좁혀 다시 조회한다.

    Returns:
        total: 조건에 맞는 전체 건수, count: 반환 건수, truncated: 잘렸는지 여부,
        results: [{WRTTIME_IDTFR_ID, WRTTIME_DESC, CLS_ID, CLS_NM, CLS_FULLNM, GRP_NM,
                   ITM_NM, ITM_FULLNM, DTA_VAL, UI_NM}]
    """
    rows, total = _run(
        reb_api.get_statistics_data,
        statbl_id=statbl_id,
        dtacycle_cd=dtacycle_cd,
        start_wrttime=start_wrttime,
        end_wrttime=end_wrttime,
        wrttime_idtfr_id=wrttime_idtfr_id,
        grp_id=grp_id,
        cls_id=cls_id,
        itm_id=itm_id,
        max_rows=max(1, max_rows),
    )
    return {
        "total": total,
        "count": len(rows),
        "truncated": total > len(rows),
        "results": [_pick(r, DATA_FIELDS) for r in rows],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="realestate-stats-mcp",
        description="한국부동산원 R-ONE 부동산통계 MCP 서버",
    )
    parser.add_argument("--transport", choices=["stdio", "http"],
                        default=os.environ.get("MCP_TRANSPORT", "stdio"),
                        help="stdio(기본) 또는 http(Streamable HTTP, 경로 /mcp)")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"),
                        help="http 모드 바인드 주소 (기본 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")),
                        help="http 모드 포트 (기본 8080)")
    args = parser.parse_args()

    _load_env()

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port, show_banner=False)
    else:
        mcp.run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
