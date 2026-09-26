"""用浏览器取回的新鲜 NBA.com 数据校验 data/nba100_*.csv。

为什么需要: 本机 stats.nba.com 只能从 nba.com 页面里取 (见 scripts/browser_collector.py)。
取回来的是一手数据, 可以用来验证 CSV 是不是忠实反映了官方接口 ——
也就是抓取/落盘环节有没有出错 (多队赛季被拆成多行、赛季漏抓、数值错位)。

覆盖范围是常规赛 + 季后赛全部赛季, 其中 **2002 年以前的季后赛** 是之前完全没校验过的部分
(Basketball-Reference 与 ESPN 在这台机器上都拿不到那份数据)。

用法:
  python scripts/browser_collector.py --out /tmp/nba_fetch --port 8899   # 终端 1
  # 浏览器在 nba.com 页面上跑 scripts/browser_fetch_snippet.js
  python scripts/verify_against_nba_api.py --fetch-dir /tmp/nba_fetch
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TOL = 0.15          # 两边都是 1 位小数, 容差给舍入
PO_FIELDS = {"GP": ("GP", 0), "MIN": ("MIN", TOL), "RPG": ("REB", TOL),
             "APG": ("AST", TOL), "FGM": ("FGM", TOL), "FGA": ("FGA", TOL),
             "FTM": ("FTM", TOL), "FTA": ("FTA", TOL), "PPG": ("PTS", TOL)}
REG_FIELDS = {"GP": ("GP", 0), "MIN": ("MIN", TOL), "PPG": ("PTS", TOL),
              "RPG": ("REB", TOL), "APG": ("AST", TOL), "FGM": ("FGM", TOL),
              "FGA": ("FGA", TOL), "FTM": ("FTM", TOL), "FTA": ("FTA", TOL)}


def load_fetch(fetch_dir: Path) -> dict[str, pd.DataFrame]:
    """把每个球员的 JSON 摊平成 DataFrame: {'playoffs': df, 'regular': df}"""
    po_rows, reg_rows, bad = [], [], []
    files = sorted(fetch_dir.glob("*.json"))
    for f in files:
        try:
            payload = json.loads(f.read_text())
            pid = int(payload["player_id"])
            sets = {s["name"]: s for s in payload["data"]["resultSets"]}
            for key, name in (("playoffs", "SeasonTotalsPostSeason"),
                              ("regular", "SeasonTotalsRegularSeason")):
                s = sets.get(name)
                if not s:
                    continue
                df = pd.DataFrame(s["rowSet"], columns=s["headers"])
                df["nba_id"] = pid
                (po_rows if key == "playoffs" else reg_rows).append(df)
        except Exception as exc:
            bad.append(f"{f.name}: {type(exc).__name__}: {exc}")
    if bad:
        print(f"  {len(bad)} 个文件解析失败: {bad[:5]}")
    return {"playoffs": pd.concat(po_rows, ignore_index=True) if po_rows else pd.DataFrame(),
            "regular": pd.concat(reg_rows, ignore_index=True) if reg_rows else pd.DataFrame()}


def collapse_multi_team(fresh: pd.DataFrame, label: str) -> pd.DataFrame:
    """多队赛季只留合并行 —— 与新抓数据里 表A/表B/TOT 三行的口径对齐。

    不做这一步就会拿"我方合并行"去挨个配对"对方的球队行", 凭空造出一堆不一致
    (第一版就是这么误报了 189 处)。
    """
    fresh = fresh.copy()
    fresh["season"] = fresh["SEASON_ID"].astype(str)
    sizes = fresh.groupby(["nba_id", "season"])["SEASON_ID"].transform("size")
    is_total = fresh["TEAM_ABBREVIATION"].astype(str).str.upper().str.fullmatch(r"\d*TOT").fillna(False)
    multi = int((sizes > 1).sum())
    kept = fresh[(sizes == 1) | is_total]
    print(f"  [{label}] 新抓 {len(fresh)} 行, 其中多队赛季 {multi} 行 "
          f"-> 取合并行后 {len(kept)} 行")
    assert kept.duplicated(["nba_id", "season"]).sum() == 0, "取合并行后仍有重复赛季"
    return kept


def compare(ours: pd.DataFrame, fresh: pd.DataFrame, fields: dict, label: str) -> pd.DataFrame:
    fresh = collapse_multi_team(fresh, label)
    m = ours.merge(fresh, on=["nba_id", "season"], how="outer", indicator=True,
                   suffixes=("", "_new"))
    print(f"\n[{label}] 本地 {len(ours)} 行, 新抓 {len(fresh)} 行 -> 合并 {len(m)} 行")
    only_ours = m[m["_merge"] == "left_only"]
    only_new = m[m["_merge"] == "right_only"]
    print(f"  仅本地有: {len(only_ours)}   仅新抓有: {len(only_new)}")
    for name, sub in (("仅本地有", only_ours), ("仅新抓有", only_new)):
        if len(sub):
            print(f"    {name} 明细 (前 10):")
            print(sub[["player", "season"]].head(10).to_string(index=False))

    rows = []
    for ours_col, (new_col, tol) in fields.items():
        a, b = m[ours_col], m[new_col]
        both = a.notna() & b.notna()
        diff = (a - b).abs()
        bad = both & (diff > tol)
        for i in m.index[bad]:
            rows.append({"player": m.at[i, "player"], "season": m.at[i, "season"],
                         "field": ours_col, "ours": m.at[i, ours_col],
                         "new": m.at[i, new_col], "delta": round(float(diff[i]), 3)})
        print(f"  {ours_col:5s} 相比: 不一致 {int(bad.sum()):3d} 处"
              f"{'' if not int(bad.sum()) else '  (最大差 ' + str(round(float(diff[bad].max()), 2)) + ')'}")
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-dir", default="/tmp/nba_fetch")
    args = ap.parse_args()
    d = Path(args.fetch_dir)
    if not list(d.glob("*.json")):
        print(f"{d} 里没有数据, 先跑收集器和浏览器脚本")
        return 2

    print("=" * 78)
    print(f"一手数据校验: {d}  ({len(list(d.glob('*.json')))} 个球员文件)")
    print("=" * 78)
    frames = load_fetch(d)
    print(f"新抓: 季后赛 {len(frames['playoffs'])} 行, 常规赛 {len(frames['regular'])} 行")

    po = pd.read_csv(DATA / "nba100_playoffs.csv")
    reg = pd.read_csv(DATA / "nba100_career_all.csv")
    reg = reg[~((reg.groupby(["player", "season"])["team"].transform("size") > 1)
                & (reg["team"].str.upper() != "TOT"))]     # 与去重后口径一致

    po_bad = compare(po, frames["playoffs"], PO_FIELDS, "季后赛 (含 2002 年前)")
    reg_bad = compare(reg, frames["regular"], REG_FIELDS, "常规赛")

    all_bad = pd.concat([po_bad, reg_bad], ignore_index=True) if len(po_bad) or len(reg_bad) else pd.DataFrame()
    print("\n" + "=" * 78)
    if len(all_bad):
        all_bad.to_csv("/tmp/nba_verify_from_api.csv", index=False)
        print(f"共 {len(all_bad)} 处不一致 -> /tmp/nba_verify_from_api.csv")
        print("\n按赛季统计 (看是不是集中在某个年代):")
        all_bad["decade"] = all_bad["season"].str[:3] + "0s"
        print(all_bad.groupby("decade").size().to_string())
        print("\n差异最大的 15 处:")
        print(all_bad.nlargest(15, "delta").to_string(index=False))
    else:
        print("全部一致 —— 本地 CSV 忠实反映了官方接口")
    return 0 if not len(all_bad) else 1


if __name__ == "__main__":
    sys.exit(main())
