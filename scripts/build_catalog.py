"""R-ONE 통계 분류 트리(All List .xls)로 src/r_one_mcp/catalog.json을 만든다.

R-ONE Open API의 통계표 목록(SttsApiTbl.do)에는 조사명·분류 경로가 없다. R-ONE 포털
'통계표 목록' 화면에서 내려받은 All List.xls(실제로는 HTML 표)의 경로를 통계표명으로 붙인다.

사용법 (저장소 루트에서, REB_API_KEY 필요):
    uv run --with pandas --with lxml python scripts/build_catalog.py "All List.xls"
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from r_one_mcp import reb_api  # noqa: E402
from r_one_mcp.server import _load_env  # noqa: E402

ROOTS = {"작성 통계리스트": "", "타기관 통계리스트": "타기관"}
OUT = Path(__file__).resolve().parents[1] / "src" / "r_one_mcp" / "catalog.json"


def main(xls: str) -> None:
    _load_env()
    df = pd.read_html(xls, encoding="utf-8")[0]
    leaf = df[df["통계표조회"].notna()]
    by_name: dict[str, list[str]] = defaultdict(list)
    for _, r in leaf.iterrows():
        parts = str(r["경로"]).split(">")
        if "자주 찾는" in str(r["경로"]) or parts[0] not in ROOTS:
            continue
        name = str(r["통계명"]).replace("└", "").strip()
        by_name[name].append(">".join(parts[1:-1]))  # 루트와 통계표명 제외

    tables = reb_api.get_all_statistics_tables(refresh=True)
    paths: dict[str, str] = {}
    per_stat: dict[str, Counter] = defaultdict(Counter)
    ambiguous = []
    for t in tables:
        cands = by_name.get(t["STATBL_NM"].strip(), [])
        if len(cands) == 1:
            paths[t["STATBL_ID"]] = cands[0]
            per_stat[t["STAT_ID"]][cands[0].split(">")[0]] += 1
        elif len(cands) > 1:
            ambiguous.append(t["STATBL_NM"])

    # 조사 ID 하나가 한 조사에만 속하면 조사명을 붙인다 (경로가 없는 통계표의 대체값)
    surveys = {sid: c.most_common(1)[0][0] for sid, c in per_stat.items() if len(c) == 1}

    OUT.write_text(json.dumps({"surveys": surveys, "tables": paths}, ensure_ascii=False, indent=0),
                   encoding="utf-8")
    print(f"tables {len(tables)}, 경로 매칭 {len(paths)}, 중복 이름 {len(ambiguous)}, 조사 {len(surveys)}")
    print("조사:", surveys)


if __name__ == "__main__":
    main(sys.argv[1])
