"""R-ONE(한국부동산원) 부동산통계 Open API 클라이언트.

MCP와 무관한 순수 클라이언트다. 다른 파이썬 코드에서 그대로 import해 써도 된다.

실측으로 확인된 사항 (DEVLOG.md 참고):
- Type=json 요청 시 서버가 한글을 깨진 바이트로 반환하는 버그가 있어, 항상 기본(XML) 응답을
  사용하고 XML을 파싱해 dict로 변환한다.
- 정상 처리 시 루트 태그는 엔드포인트명(예: <SttsApiTblData>)이고 그 아래 <head><RESULT>에
  CODE/MESSAGE가 있다. 에러 시(ERROR-300 등)에는 <head> 없이 루트가 바로 <RESULT>다.
- SttsApiTbl.do는 STATBL_ID 없이 호출하면 전체 통계표 목록을 반환한다. 이를 디스크에 캐시해
  키워드 검색에 쓴다 (일별 트래픽 제한 때문에 매번 받지 않는다).
"""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

BASE_URL = "https://www.reb.or.kr/r-one/openapi"
MAX_PAGE_SIZE = 1000

ERROR_MESSAGES = {
    "ERROR-300": "필수 값 누락",
    "ERROR-290": "인증키가 유효하지 않음 (R-ONE 사이트에서 직접 발급받은 키가 맞는지 확인 필요)",
    "ERROR-336": "1회 최대 1,000건 초과 요청",
    "ERROR-337": "일별 트래픽 제한 초과 (익일 재시도)",
    "ERROR-333": "요청위치(pIndex) 타입 오류",
    "ERROR-310": "서비스를 찾을 수 없음",
    "ERROR-500": "서버 오류",
    "ERROR-600": "DB 연결 오류",
    "ERROR-601": "SQL 오류",
}


class RebApiError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


# --- 설정 -----------------------------------------------------------------

def _get_api_key() -> str:
    key = os.environ.get("REB_API_KEY", "").strip()
    if not key:
        raise RebApiError(
            "NO-KEY",
            "REB_API_KEY가 설정되지 않았습니다. MCP 클라이언트 설정의 env 항목이나 "
            "프로젝트 폴더의 .env 파일에 REB_API_KEY를 넣어주세요.",
        )
    return key


def _cache_dir() -> Path:
    custom = os.environ.get("REB_CACHE_DIR")
    if custom:
        return Path(custom)
    base = os.environ.get("XDG_CACHE_HOME") or os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "r-one-mcp"


def _cache_ttl_seconds() -> float:
    try:
        days = float(os.environ.get("REB_CACHE_TTL_DAYS", "7"))
    except ValueError:
        days = 7
    return days * 24 * 60 * 60


# --- HTTP 호출 --------------------------------------------------------------

_client: httpx.Client | None = None


def _http() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=30)
    return _client


def _row_to_dict(row: ET.Element) -> dict:
    return {child.tag: (child.text or "") for child in row}


def _call(endpoint: str, params: dict) -> tuple[list[dict], int]:
    """R-ONE 엔드포인트를 호출해 (row 목록, list_total_count)를 반환한다."""
    query = {"KEY": _get_api_key(), "pIndex": 1, "pSize": 100}
    query.update(params)

    try:
        resp = _http().get(f"{BASE_URL}/{endpoint}", params=query)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise RebApiError("HTTP", f"R-ONE 서버 호출 실패: {e}") from e

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        raise RebApiError("PARSE", f"응답 XML을 해석할 수 없습니다: {resp.text[:300]}") from e

    # 에러 시 루트가 바로 <RESULT>, 정상 시 <head><RESULT>
    result = root if root.tag == "RESULT" else root.find("head/RESULT")
    code = result.findtext("CODE") if result is not None else None
    message = result.findtext("MESSAGE") if result is not None else None

    if code is None:
        raise RebApiError("UNKNOWN", f"응답 형식을 해석할 수 없습니다: {resp.text[:300]}")
    if code == "INFO-200":
        return [], 0
    if code != "INFO-000":
        raise RebApiError(code, ERROR_MESSAGES.get(code, message or "알 수 없는 오류"))

    total_text = root.findtext("head/list_total_count")
    total = int(total_text) if total_text else 0
    return [_row_to_dict(r) for r in root.findall("row")], total


def _call_pages(endpoint: str, params: dict, max_rows: int | None = None,
                page_size: int = MAX_PAGE_SIZE) -> tuple[list[dict], int]:
    """페이지를 순회하며 row를 모은다. (row 목록, 전체 건수)를 반환한다.

    max_rows를 주면 그만큼만 모으고 멈춘다 (트래픽 절약).
    """
    rows: list[dict] = []
    total = 0
    page = 1
    while True:
        size = page_size if max_rows is None else min(page_size, max_rows - len(rows))
        batch, total = _call(endpoint, {**params, "pIndex": page, "pSize": size})
        rows.extend(batch)
        if not batch or len(rows) >= total or (max_rows is not None and len(rows) >= max_rows):
            break
        page += 1
    return rows, total


# --- 통계표 목록 (디스크 캐시) ------------------------------------------------

_table_list_cache: list[dict] | None = None


def get_all_statistics_tables(refresh: bool = False) -> list[dict]:
    """전체 통계표 목록. 메모리 → 디스크 캐시(기본 7일) → API 순으로 찾는다."""
    global _table_list_cache
    if _table_list_cache is not None and not refresh:
        return _table_list_cache

    cache_file = _cache_dir() / "tables.json"
    if not refresh and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < _cache_ttl_seconds():
            try:
                _table_list_cache = json.loads(cache_file.read_text(encoding="utf-8"))
                return _table_list_cache
            except (OSError, json.JSONDecodeError):
                pass

    tables, _ = _call_pages("SttsApiTbl.do", {})
    _table_list_cache = tables
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # 캐시 저장 실패는 무시 (메모리 캐시는 유지)
    return tables


# 검색어에 들어온 주기 표현 → 주기코드. 통계표명에는 "(주)", "(월)"처럼만 적혀 있어서
# "주간", "월별" 같은 말로는 이름 매칭이 안 되므로 주기 필터로 바꿔 처리한다.
CYCLE_WORDS = {
    "주간": "WK", "주별": "WK", "주단위": "WK", "(주)": "WK", "weekly": "WK",
    "월간": "MM", "월별": "MM", "(월)": "MM", "monthly": "MM",
    "분기": "QY", "분기별": "QY", "(분기)": "QY", "quarterly": "QY",
    "반기": "HY", "반기별": "HY", "(반기)": "HY",
    "연간": "YY", "연도별": "YY", "년별": "YY", "연별": "YY", "(연)": "YY", "yearly": "YY", "annual": "YY",
}


# API의 통계표 목록에는 조사 ID(STAT_ID)만 있고 조사명·분류 경로가 없다.
# R-ONE 포털 분류 트리(All List.xls)로 만든 catalog.json에서 경로를 붙인다
# (예: 전국주택가격동향조사 > 주간아파트동향 > 매매가격지수). 다시 만들려면 scripts/build_catalog.py.
# 주간 통계표는 이름에 "아파트"가 없지만 경로에 "주간아파트동향"이 있어 검색에 걸린다.
def _load_catalog() -> dict:
    try:
        return json.loads((Path(__file__).with_name("catalog.json")).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"surveys": {}, "tables": {}}


_CATALOG = _load_catalog()


def survey_info(t: dict) -> tuple[str, str]:
    """통계표의 (조사명, 하위 분류 경로)를 돌려준다. 모르면 빈 문자열."""
    path = _CATALOG["tables"].get(t.get("STATBL_ID", ""))
    if path:
        survey, _, section = path.partition(">")
        return survey, section
    return _CATALOG["surveys"].get(t.get("STAT_ID", ""), ""), ""


# 분류 경로별 해석 주의. 통계표 이름만 보고는 알 수 없는 사실을 검색·조회 결과에 붙인다.
TABLE_NOTES = {
    "전국주택가격동향조사>주간아파트동향": (
        "주간아파트동향은 아파트만 조사한다. 표 이름에 '아파트'가 없어도 아파트 지수다 "
        "(주택종합·연립·단독은 월간동향에 있다)."
    ),
    "전국주택가격동향조사>월간동향": (
        "월간동향은 주택유형별로 표가 나뉜다 (표 이름 끝의 _아파트/_연립다세대/_단독주택/_주택종합)."
    ),
}


def table_note(statbl_id: str) -> str:
    """통계표의 해석 주의 문구. 없으면 빈 문자열."""
    path = _CATALOG["tables"].get(statbl_id, "")
    return " ".join(n for prefix, n in TABLE_NOTES.items() if path.startswith(prefix))


def _norm(s: str) -> str:
    return s.replace(" ", "").lower()


def _cycles(t: dict) -> list[str]:
    return (t.get("DTACYCLE_CD") or "").replace(" ", "").split(",")


def search_statistics_tables(keyword: str, cycle: str | None = None) -> tuple[list[dict], dict]:
    """통계표명으로 통계표를 찾는다. (결과, 검색 정보)를 반환한다.

    - 키워드를 공백으로 나눠 모든 단어가 통계표명 또는 조사명·하위 분류에 들어간 표를 찾는다
      (순서·띄어쓰기 무관). 예: "아파트 주간 매매" → 주간아파트동향의 (주) 매매가격지수.
    - "주간", "월별", "분기" 같은 주기 표현은 이름 매칭 대신 주기 필터로 쓴다.
    - 모든 단어가 맞는 표가 없으면, 가장 많은 단어가 맞는 표를 대신 돌려준다.
    """
    cycle = cycle.strip().upper() if cycle else None
    tokens: list[str] = []
    for raw in keyword.split():
        tok = _norm(raw)
        if tok in CYCLE_WORDS:
            cycle = cycle or CYCLE_WORDS[tok]
        elif tok:
            tokens.append(tok)

    tables = [t for t in get_all_statistics_tables() if not cycle or cycle in _cycles(t)]
    scored = []
    for t in tables:
        name = _norm(" ".join((t.get("STATBL_NM", ""), *survey_info(t))))
        hits = sum(tok in name for tok in tokens)
        scored.append((hits, t))

    info: dict = {"tokens": tokens, "cycle": cycle, "match": "all"}
    full = [t for hits, t in scored if hits == len(tokens)]
    if full or not tokens:
        return full, info

    best = max((hits for hits, _ in scored), default=0)
    if best == 0:
        info["match"] = "none"
        return [], info
    partial = [t for hits, t in scored if hits == best]
    name_all = " ".join(_norm(" ".join((t.get("STATBL_NM", ""), *survey_info(t)))) for t in partial)
    info["match"] = "partial"
    info["unmatched_tokens"] = [tok for tok in tokens if tok not in name_all]
    return partial, info


# --- 항목 / 데이터 -----------------------------------------------------------

def get_statistics_items(statbl_id: str, itm_tag: str | None = None) -> list[dict]:
    params = {"STATBL_ID": statbl_id}
    if itm_tag:
        params["ITM_TAG"] = itm_tag
    rows, _ = _call_pages("SttsApiTblItm.do", params)
    return rows


def get_statistics_data(
    statbl_id: str,
    dtacycle_cd: str,
    start_wrttime: str | None = None,
    end_wrttime: str | None = None,
    wrttime_idtfr_id: str | None = None,
    grp_id: str | None = None,
    cls_id: str | None = None,
    itm_id: str | None = None,
    max_rows: int | None = None,
) -> tuple[list[dict], int]:
    """(row 목록, 조건에 맞는 전체 건수)를 반환한다."""
    params = {"STATBL_ID": statbl_id, "DTACYCLE_CD": dtacycle_cd.upper()}
    optional = {
        "START_WRTTIME": start_wrttime,
        "END_WRTTIME": end_wrttime,
        "WRTTIME_IDTFR_ID": wrttime_idtfr_id,
        "GRP_ID": grp_id,
        "CLS_ID": cls_id,
        "ITM_ID": itm_id,
    }
    params.update({k: v for k, v in optional.items() if v})
    return _call_pages("SttsApiTblData.do", params, max_rows=max_rows)


# --- 지역(분류) 필터 ---------------------------------------------------------
#
# R-ONE의 CLS_ID 필터는 코드 하나만 받고, 상위 코드(예: 서울)를 주면 그 합계 1건만 나온다.
# "서울의 모든 구"처럼 여러 분류를 받으려면 (a) 코드마다 따로 호출하거나 (b) 전체를 받아 걸러야 한다.
# 아래 함수는 두 방법 중 R-ONE 호출 수가 적은 쪽을 고른다.

_class_cache: dict[str, list[dict]] = {}


def get_classes(statbl_id: str) -> list[dict]:
    """통계표의 '분류' 항목 목록 (프로세스 동안 캐시)."""
    if statbl_id not in _class_cache:
        _class_cache[statbl_id] = get_statistics_items(statbl_id, "분류")
    return _class_cache[statbl_id]


def resolve_regions(statbl_id: str, region: str, leaf_only: bool = False) -> tuple[list[dict], list[str]]:
    """지역(분류) 이름으로 CLS 항목을 찾는다. (찾은 항목, 못 찾은 이름)을 반환한다.

    region은 쉼표로 여러 개를 줄 수 있다. 각 이름은
    - 전체 경로("서울>강남지역>동남권")와 같거나
    - 항목명("동남권", "강남구")과 같은 항목을 찾고, 그 아래 하위 항목을 모두 포함한다.
    같은 이름이 여러 곳에 있으면(예: "중구") 모두 포함하므로, 좁히려면 "서울>강북지역>도심권>중구"처럼
    경로로 쓰거나 상위 지역과 함께 "서울>중구"처럼 쓴다 (경로의 첫 부분과 마지막 이름으로 찾는다).
    leaf_only=True면 하위 항목이 없는 말단(예: 구)만 남긴다.
    """
    classes = get_classes(statbl_id)
    by_id = {c["ITM_ID"]: c for c in classes}
    children: dict[str, list[str]] = {}
    for c in classes:
        children.setdefault(c.get("PAR_ITM_ID", ""), []).append(c["ITM_ID"])

    def path(c: dict) -> str:
        return _norm(c.get("ITM_FULLNM") or c.get("ITM_NM") or "")

    picked: dict[str, dict] = {}
    missing: list[str] = []
    for raw in region.split(","):
        name = _norm(raw)
        if not name:
            continue
        head, _, tail = name.partition(">")
        last = name.rsplit(">", 1)[-1]
        roots = [
            c for c in classes
            if path(c) == name
            or _norm(c.get("ITM_NM", "")) == name
            or (tail and path(c).startswith(head + ">") and _norm(c.get("ITM_NM", "")) == last)
        ]
        if not roots:
            missing.append(raw.strip())
            continue
        stack = [c["ITM_ID"] for c in roots]
        while stack:
            cid = stack.pop()
            if cid in by_id and cid not in picked:
                picked[cid] = by_id[cid]
                stack.extend(children.get(cid, []))

    result = list(picked.values())
    if leaf_only:
        result = [c for c in result if not children.get(c["ITM_ID"])]
    result.sort(key=lambda c: int(c["ITM_ID"]) if c["ITM_ID"].isdigit() else 0)
    return result, missing


def get_statistics_data_multi(
    statbl_id: str,
    dtacycle_cd: str,
    cls_ids: list[str],
    **kwargs,
) -> tuple[list[dict], int, dict]:
    """여러 CLS_ID의 데이터를 모은다. (row 목록, 건수, 조회 방식 정보)를 반환한다."""
    wanted = list(dict.fromkeys(cls_ids))
    if len(wanted) == 1:
        rows, total = get_statistics_data(statbl_id, dtacycle_cd, cls_id=wanted[0], **kwargs)
        return rows, total, {"strategy": "single", "api_calls": max(1, -(-total // MAX_PAGE_SIZE))}

    # 전체 건수를 1건짜리 호출로 알아낸 뒤 호출 수를 비교한다.
    _, total_all = get_statistics_data(statbl_id, dtacycle_cd, max_rows=1, **kwargs)
    n_classes = max(1, len(get_classes(statbl_id)))
    per_code_pages = max(1, -(-int(total_all / n_classes) // MAX_PAGE_SIZE))
    per_code_calls = len(wanted) * per_code_pages
    full_calls = max(1, -(-total_all // MAX_PAGE_SIZE))

    if per_code_calls <= full_calls:
        rows: list[dict] = []
        for cid in wanted:
            part, _ = get_statistics_data(statbl_id, dtacycle_cd, cls_id=cid, **kwargs)
            rows.extend(part)
        info = {"strategy": "per_code", "api_calls": 1 + per_code_calls}
    else:
        allrows, _ = get_statistics_data(statbl_id, dtacycle_cd, **kwargs)
        keep = set(wanted)
        rows = [r for r in allrows if r.get("CLS_ID") in keep]
        info = {"strategy": "full_then_filter", "api_calls": 1 + full_calls}
    return rows, len(rows), info
