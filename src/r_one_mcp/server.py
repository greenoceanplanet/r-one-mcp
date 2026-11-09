"""r-one-mcp — 한국부동산원(R-ONE) 부동산통계 범용 조회 MCP 서버.

특정 클라이언트에 묶이지 않도록 표준 MCP만 사용한다.
- 기본: stdio (Claude Code/Desktop, Cursor, Codex, Gemini CLI, VS Code 등 대부분의 에이전트)
- 선택: --transport http (Streamable HTTP만 지원하는 클라이언트·원격 접속용)

R-ONE API는 통계표코드(STATBL_ID)로 통계를 고르는 구조라, 통계표별 툴을 만들지 않고
3개의 범용 툴로 모든 통계표를 다룬다.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
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

통계 해석 주의:
- 주간 통계표((주) 매매가격지수, (주) 전세가격지수 등)는 전국주택가격동향조사의 '주간아파트동향'으로,
  아파트만 대상이다. 표 이름에 '아파트'가 없어도 아파트 지수로 설명한다.
- 월간동향은 주택유형별(아파트/연립다세대/단독주택/주택종합)로 표가 나뉜다.
- 검색·조회 결과에 NOTE/note가 있으면 그 내용을 답변에 반영한다.

주의: R-ONE API는 일별 트래픽 제한이 있으므로 기간·지역을 좁혀서 조회한다.
결과가 크면 get_statistics_data의 save_csv로 파일에 저장한다. 서버는 사용자의 프로젝트 폴더를 모르므로,
사용자가 작업 중인 폴더가 있으면 그 안의 절대경로(예: <프로젝트>/data/파일명.csv)를 넘긴다.
"""

mcp = FastMCP("r-one-mcp", instructions=INSTRUCTIONS, version=__version__)


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
               "GRP_ID", "GRP_NM", "ITM_ID", "ITM_NM", "ITM_FULLNM", "DTA_VAL", "UI_NM")


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True})
def search_statistics(keyword: str, cycle: str | None = None, limit: int = 50) -> dict:
    """R-ONE 통계표를 이름으로 검색한다.

    키워드를 공백으로 나눈 모든 단어가 통계표명 또는 조사명(SURVEY_NM)·하위 분류(SECTION_NM)에
    들어간 항목을 찾는다 (순서·띄어쓰기 무관). 빈 문자열이면 전체 목록.
    예: "아파트 주간 매매", "전세 지수", "지가", "실거래 아파트", "임대동향 공실률".
    "주간/월간/분기/반기/연간" 같은 주기 표현은 주기 필터로 처리한다.
    모든 단어가 맞는 표가 없으면 가장 많이 맞는 표를 돌려주고 match="partial"로 알린다.

    참고: 주간아파트동향(전국주택가격동향조사) 통계표는 이름이 "(주) 매매가격지수"처럼 되어 있어
    "아파트"가 없지만 조사 분류로 찾힌다. 통계표 목록은 로컬에 캐시된다(기본 7일).

    Args:
        keyword: 통계표명 검색어
        cycle: 주기 필터. YY(년)/HY(반기)/QY(분기)/MM(월)/WK(주) 중 하나 (옵션)
        limit: 최대 반환 건수 (기본 50)

    Returns:
        match: "all"(모든 단어 일치) / "partial"(일부 단어만 일치) / "none",
        unmatched_tokens: partial일 때 어느 표에도 없던 단어,
        cycle: 실제 적용된 주기 필터, total: 검색된 전체 건수, count: 반환 건수,
        results: [{STATBL_ID, STATBL_NM, SURVEY_NM(조사명), SECTION_NM(조사 안의 분류 경로, 예: "주간아파트동향>매매가격지수"),
                   DTACYCLE_CD(쉼표로 여러 주기 가능), DTACYCLE_NM,
                   DATA_START_YY, DATA_END_YY(목록 메타값이라 실제 최신 시점보다 늦을 수 있음),
                   RPSTUI_NM(기준시점)}]
    """
    rows, info = _run(reb_api.search_statistics_tables, keyword, cycle)

    def table(r: dict) -> dict:
        survey, section = reb_api.survey_info(r)
        d = _pick(r, TABLE_FIELDS)
        d["SURVEY_NM"] = survey or None
        d["SECTION_NM"] = section or None
        note = reb_api.table_note(r.get("STATBL_ID", ""))
        if note:
            d["NOTE"] = note
        return d

    limit = max(1, limit)
    out = {"match": info["match"], "cycle": info["cycle"]}
    if info["match"] == "partial":
        out["unmatched_tokens"] = info["unmatched_tokens"]
        out["note"] = "모든 단어가 들어간 통계표가 없어 가장 많이 일치하는 표를 보여줍니다."
    elif info["match"] == "none":
        out["note"] = "일치하는 통계표가 없습니다. 더 짧은 단어(예: '매매', '전세', '지가')로 검색해 보세요."
    out.update({
        "total": len(rows),
        "count": min(len(rows), limit),
        "results": [table(r) for r in rows[:limit]],
    })
    return out


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


def _output_base() -> tuple[Path, str]:
    """상대경로 저장의 기준 폴더와 그 출처. REB_OUTPUT_DIR → ~/r-one-data.

    stdio 서버의 cwd는 클라이언트마다 달라서(uv run --directory면 이 저장소 폴더) 쓰지 않는다.
    서버는 사용자의 프로젝트 폴더를 알 수 없으므로(MCP roots는 2026-07 스펙에서 폐기 예정),
    프로젝트에 저장하려면 에이전트가 절대경로를 넘긴다.
    """
    env = os.environ.get("REB_OUTPUT_DIR")
    if env:
        return Path(env).expanduser(), "REB_OUTPUT_DIR"
    return Path.home() / "r-one-data", "home"


def _resolve_csv_path(save_csv: str, statbl_id: str, base: Path) -> Path:
    """저장 경로를 정한다. 같은 이름이 있으면 덮어쓰지 않고 번호를 붙인다."""
    path = Path(save_csv).expanduser()
    if save_csv.strip() in ("", ".", "auto"):
        path = Path(f"{statbl_id}.csv")
    if not path.is_absolute():
        path = base / path
    if path.suffix.lower() != ".csv":
        path = path.with_suffix(".csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    stem, n = path.stem, 1
    while path.exists():
        path = path.with_name(f"{stem}_{n}.csv")
        n += 1
    return path


@mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})
async def get_statistics_data(
    statbl_id: str,
    dtacycle_cd: str,
    start_wrttime: str | None = None,
    end_wrttime: str | None = None,
    wrttime_idtfr_id: str | None = None,
    grp_id: str | None = None,
    cls_id: str | None = None,
    itm_id: str | None = None,
    region: str | None = None,
    leaf_only: bool = False,
    max_rows: int = 1000,
    save_csv: str | None = None,
) -> dict:
    """통계표의 실제 수치를 조회한다. save_csv를 주면 CSV 파일로 저장하고 미리보기만 돌려준다.

    시점 형식은 주기코드(dtacycle_cd)에 따라 다르다 (start/end/wrttime_idtfr_id 공통):
        YY(년)   YYYY            예: 2024
        HY(반기) YYYY0X (X=1,2)  예: 202301
        QY(분기) YYYY0X (X=1~4)  예: 202304
        MM(월)   YYYYMM          예: 202412
        WK(주)   YYYYWW          예: 202452
    start/end에는 연도(YYYY)만 넣어도 된다 (MM 주기에 start_wrttime="2026"이면 2026년 1월부터).

    지역 여러 곳을 한 번에 받으려면 region을 쓴다. 예: region="서울", leaf_only=True → 서울 25개 구만.
    R-ONE은 상위 지역 코드(서울)를 주면 그 합계 1건만 주므로, 하위 지역이 필요하면 cls_id 대신 region을 쓴다.
    서버가 '코드별 호출'과 '전체 조회 후 걸러내기' 중 R-ONE 호출이 적은 쪽을 고른다.

    grp_id/cls_id/itm_id는 get_statistics_items로 확인한다. 일부만 채워도 된다.
    itm_id를 비우면 항목이 여러 개인 표(예: 변동률·누계)는 같은 시점이 항목별로 중복되어 나오므로,
    필요한 항목이 정해져 있으면 itm_id를 지정한다.
    존재하지 않는 코드를 넣으면 에러 없이 빈 결과(count=0)가 나온다.

    Args:
        statbl_id: 통계표ID (필수)
        dtacycle_cd: 주기코드 YY/HY/QY/MM/WK (필수)
        start_wrttime / end_wrttime: 조회 기간 (옵션)
        wrttime_idtfr_id: 특정 시점 하나만 조회 (옵션)
        grp_id / cls_id / itm_id: 그룹 / 분류(주로 지역) / 항목 필터 (옵션). cls_id는 쉼표로 여러 개 가능.
        region: 분류(주로 지역) 이름으로 거르기 (옵션, 쉼표로 여러 개). 그 지역과 하위 지역을 모두 포함한다.
            예: "서울", "서울>강남지역>동남권", "동남권", "서울,경기", "서울>중구"(같은 이름 구분용).
        leaf_only: region으로 찾은 것 중 하위가 없는 말단(예: 구)만 남김 (기본 False → 서울·권역 합계 포함)
        max_rows: 최대 조회 건수 (기본 1000). truncated=true면 조건을 좁히거나 늘려 다시 조회한다.
        save_csv: CSV 저장 경로 (옵션). 결과가 크면 이 옵션을 쓰는 편이 낫다.
            - 사용자가 작업 중인 프로젝트 폴더가 있으면 그 안의 절대경로를 넘긴다
              (예: "D:/projects/my-analysis/data/seoul_weekly.csv"). 서버는 프로젝트 폴더를 알 수 없다.
            - 파일명·상대경로만 주면 REB_OUTPUT_DIR(설정 시) 또는 ~/r-one-data 아래에 저장한다.
              "auto"면 <STATBL_ID>.csv.
            - 같은 이름이 있으면 덮어쓰지 않고 _1, _2를 붙인다. 엑셀용 UTF-8(BOM)으로 저장한다.

    Returns:
        total: 조건에 맞는 전체 건수, count: 가져온 건수, truncated: 잘렸는지 여부,
        items: 결과에 섞여 있는 항목명 목록 (2개 이상이면 항목별로 나눠 읽을 것),
        results: [{WRTTIME_IDTFR_ID, WRTTIME_DESC, CLS_ID, CLS_NM, CLS_FULLNM, GRP_ID, GRP_NM,
                   ITM_ID, ITM_NM, ITM_FULLNM, DTA_VAL, UI_NM}]
        note: 통계표 해석 주의 (있을 때만, 예: 주간아파트동향은 아파트만 대상)
        region/cls_id 여러 개를 쓴 경우: regions(포함된 분류 경로 목록), regions_missing(못 찾은 이름),
            fetch(strategy: per_code/full_then_filter, api_calls: R-ONE 호출 수)
        save_csv를 준 경우: results 대신 saved_path(저장된 파일 경로), saved_base(기준 폴더를 정한 방식:
            absolute/REB_OUTPUT_DIR/home), preview(앞 5건)
    """
    common = dict(start_wrttime=start_wrttime, end_wrttime=end_wrttime,
                  wrttime_idtfr_id=wrttime_idtfr_id, grp_id=grp_id, itm_id=itm_id)
    max_rows = max(1, max_rows)
    codes = [c.strip() for c in (cls_id or "").split(",") if c.strip()]
    extra: dict = {}
    if region:
        found, missing = await asyncio.to_thread(_run, reb_api.resolve_regions, statbl_id, region, leaf_only)
        if not found and not codes:
            raise ToolError(f"'{region}'에 해당하는 분류가 없습니다. get_statistics_items(itm_tag='분류')로 "
                            "이름을 확인하세요.")
        codes += [c["ITM_ID"] for c in found]
        extra["regions"] = [c.get("ITM_FULLNM") or c.get("ITM_NM") for c in found]
        if missing:
            extra["regions_missing"] = missing

    if len(codes) <= 1:
        rows, total = await asyncio.to_thread(
            _run, reb_api.get_statistics_data, statbl_id=statbl_id, dtacycle_cd=dtacycle_cd,
            cls_id=codes[0] if codes else None, max_rows=max_rows, **common)
    else:
        rows, total, info = await asyncio.to_thread(
            _run, reb_api.get_statistics_data_multi, statbl_id, dtacycle_cd, codes, **common)
        rows = rows[:max_rows]
        extra["fetch"] = info
    picked = [_pick(r, DATA_FIELDS) for r in rows]
    out = {
        "total": total,
        "count": len(rows),
        "truncated": total > len(rows),
        "items": sorted({r.get("ITM_NM") or "" for r in rows}),
    }
    out.update(extra)
    note = reb_api.table_note(statbl_id)
    if note:
        out["note"] = note
    if save_csv is None:
        out["results"] = picked
        return out

    if Path(save_csv).expanduser().is_absolute():
        base, how = Path(), "absolute"
    else:
        base, how = _output_base()
    path = _resolve_csv_path(save_csv, statbl_id, base)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=("STATBL_ID", *DATA_FIELDS))
        w.writeheader()
        for r in picked:
            w.writerow({"STATBL_ID": statbl_id, **r})
    out["saved_path"] = str(path)
    out["saved_base"] = how
    out["preview"] = picked[:5]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="r-one-mcp",
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
