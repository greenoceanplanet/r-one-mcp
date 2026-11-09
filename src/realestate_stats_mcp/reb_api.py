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
    return root / "realestate-stats-mcp"


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


def search_statistics_tables(keyword: str, cycle: str | None = None) -> list[dict]:
    """통계표명에 키워드의 모든 단어가 들어간 통계표를 찾는다.

    "아파트 매매" → "아파트"와 "매매"가 모두 들어간 통계표 (순서·붙여쓰기 무관).
    cycle을 주면 해당 주기(YY/HY/QY/MM/WK)를 지원하는 통계표만 남긴다.
    """
    def norm(s: str) -> str:
        return s.replace(" ", "").lower()

    tokens = [norm(t) for t in keyword.split() if t.strip()]
    cycle = cycle.strip().upper() if cycle else None
    out = []
    for t in get_all_statistics_tables():
        name = norm(t.get("STATBL_NM", ""))
        if not all(tok in name for tok in tokens):
            continue
        if cycle and cycle not in (t.get("DTACYCLE_CD") or "").replace(" ", "").split(","):
            continue
        out.append(t)
    return out


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
