"""
季后赛数据校验与补齐 (ESPN / hoopR 数据源, 独立于 NBA.com 和 Basketball-Reference)

数据源: https://github.com/sportsdataverse/hoopR-nba-data  (nba/player_box/parquet)
  逐场 box score, season_type==3 即季后赛。按球员-赛季聚合得到季后赛场均数据。
  覆盖范围: 2002-至今 (更早的赛季 ESPN 没有逐场数据)

两个用途:
  1. 校验: 把 data/nba100_playoffs.csv 与 ESPN 聚合结果逐季比对
  2. 补齐: 导出 2025-26 季后赛聚合结果, 供 scripts/patch_current_season.py 使用

已知来源差异 (不是错误, 已在容差内):
  - 出场时间 ESPN 比 NBA.com 官方系统性低约 0.2 分钟
  - ESPN 个别场次的 box score 缺失 (如 2006 季后赛), 会导致 GP 少 1

用法:
  python scripts/verify_playoffs_espn.py --cache /tmp/nba_verify/hoopr
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = "https://raw.githubusercontent.com/sportsdataverse/hoopR-nba-data/main/nba/player_box/parquet"
SEASONS = range(2002, 2027)
TOL = 0.15
MIN_TOL = 0.5
# 归一化保留 Jr./II/III 后缀, 否则 Gary Payton 会与 Gary Payton II 撞名
# (对照脚本 verify_reference_data.py 相反 —— 那边 B-R 用 "Jimmy Butler III", 必须去后缀)
EXTRA_NAMES = {
    "jimmy butler": ["jimmy butler iii"],
    "nate archibald": ["tiny archibald"],
}
FIELDS = {
    "GP": ("GP", 0.0),
    "MIN": ("MIN", MIN_TOL),
    "PPG": ("PPG", TOL),
    "RPG": ("RPG", TOL),
    "APG": ("APG", TOL),
    "FGM": ("FGM", TOL),
    "FGA": ("FGA", TOL),
    "FTM": ("FTM", TOL),
    "FTA": ("FTA", TOL),
}


def normalize(name: str) -> str:
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower().replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(n.split())


def name_keys(player: str) -> set[str]:
    keys = {normalize(player)}
    keys |= set(EXTRA_NAMES.get(normalize(player), []))
    return keys


def to_end_year(season: str) -> int:
    return int(str(season)[:4]) + 1


def fetch_box(cache: Path, season: int) -> pd.DataFrame | None:
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"player_box_{season}.parquet"
    if not f.exists():
        r = requests.get(f"{BASE}/{f.name}", headers={"User-Agent": "Mozilla/5.0"}, timeout=180)
        if r.status_code != 200:
            print(f"    {season}: HTTP {r.status_code}")
            return None
        f.write_bytes(r.content)
    return pd.read_parquet(f)


def build_espn_playoffs(cache: Path, seasons) -> pd.DataFrame:
    frames = []
    for s in seasons:
        df = fetch_box(cache, s)
        if df is None:
            continue
        # 不能用 did_not_play 过滤 —— 该字段在 ESPN 数据里不可靠
        # (实测 Chris Bosh 2011-12: 23 场全部 did_not_play=False, 但只有 14 场有出场时间)
        po = df[(df["season_type"] == 3) & (df["minutes"] > 0)].copy()
        if po.empty:
            continue
        po["end_year"] = po["season"].astype(int)
        g = po.groupby(["athlete_display_name", "end_year"]).agg(
            GP=("game_id", "count"),
            MIN=("minutes", "mean"),
            PPG=("points", "mean"),
            RPG=("rebounds", "mean"),
            APG=("assists", "mean"),
            FGM=("field_goals_made", "mean"),
            FGA=("field_goals_attempted", "mean"),
            FTM=("free_throws_made", "mean"),
            FTA=("free_throws_attempted", "mean"),
        ).reset_index().rename(columns={"athlete_display_name": "player"})
        frames.append(g)
    out = pd.concat(frames, ignore_index=True)
    for c in ["MIN", "PPG", "RPG", "APG", "FGM", "FGA", "FTM", "FTA"]:
        out[c] = out[c].round(1)
    out["norm"] = out["player"].map(normalize)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/tmp/nba_verify/hoopr")
    ap.add_argument("--patch-out", default="/tmp/nba_verify/playoffs_2026.csv")
    args = ap.parse_args()

    ours = pd.read_csv(DATA / "nba100_playoffs.csv")
    ours["end_year"] = ours["season"].map(to_end_year)

    print("=" * 80)
    print("季后赛校验: data/nba100_playoffs.csv  vs  ESPN 逐场数据 (hoopR)")
    print("=" * 80)
    print("读取 hoopR player_box ...")
    espn = build_espn_playoffs(Path(args.cache), SEASONS)
    print(f"ESPN 季后赛聚合: {len(espn)} 个球员赛季 (season {min(SEASONS)}-{max(SEASONS)})")

    key_to_player = {}
    for p in ours["player"].unique():
        for k in name_keys(p):
            key_to_player[k] = p
    espn = espn[espn["norm"].isin(key_to_player)].copy()
    espn["our_player"] = espn["norm"].map(key_to_player)
    idx = {p: g for p, g in espn.groupby("our_player")}

    mismatches, checked, skipped = [], 0, 0
    covered_from = min(SEASONS)
    for player in sorted(ours["player"].unique()):
        g_ours = ours[ours["player"] == player]
        g_ref = idx.get(player)
        for _, o in g_ours.iterrows():
            if o["end_year"] < covered_from:
                skipped += 1
                continue
            if g_ref is None:
                mismatches.append({"player": player, "season": o["season"], "field": "(缺行)",
                                   "ours": f"GP={o['GP']:.0f}", "ref": "", "delta": None, "kind": "missing"})
                continue
            r = g_ref[g_ref["end_year"] == o["end_year"]]
            if r.empty:
                mismatches.append({"player": player, "season": o["season"], "field": "(缺行)",
                                   "ours": f"GP={o['GP']:.0f}", "ref": "ESPN 无该赛季", "delta": None,
                                   "kind": "missing"})
                continue
            r = r.iloc[0]
            checked += 1
            for c, (ec, tol) in FIELDS.items():
                ov, rv = o.get(c), r.get(ec)
                if pd.isna(ov) or pd.isna(rv):
                    continue
                d = abs(float(ov) - float(rv))
                if d > tol:
                    mismatches.append({"player": player, "season": o["season"], "field": c,
                                       "ours": ov, "ref": rv, "delta": round(d, 3), "kind": "value"})

    # ESPN 有、我们完全没有的球员赛季
    for _, r in espn.groupby(["our_player", "end_year"]).size().reset_index(name="n").iterrows():
        has = ((ours["player"] == r["our_player"]) & (ours["end_year"] == r["end_year"])).any()
        if not has:
            mismatches.append({"player": r["our_player"], "season": int(r["end_year"]), "field": "(缺赛季)",
                               "ours": "", "ref": f"GP={r['n']:.0f}", "delta": None, "kind": "missing"})

    print(f"\n已核对 {checked} 个球员赛季 (ESPN 覆盖 {covered_from}+; 跳过 {skipped} 个更早赛季)")
    print(f"MIN 容差 ±{MIN_TOL} (ESPN 出场时间与 NBA.com 存在系统性 ~0.2 分钟差异)")
    mm = pd.DataFrame(mismatches)
    if len(mm):
        mm.to_csv("/tmp/nba_verify/playoff_mismatches.csv", index=False)
        mm["hist"] = mm["season"].astype(str).str[:4].astype(int) < 2025
        print(f"不符 {len(mm)} 处 (历史 {int(mm['hist'].sum())} / 当季 {int((~mm['hist']).sum())})")
        print(mm.groupby(["field", "kind"]).size().to_string())
        h = mm[mm["hist"]]
        if len(h):
            print("\n历史赛季差异:")
            print(h.to_string(index=False))
    else:
        print("无数值不符")

    patch = espn[(espn["end_year"] == 2026)].copy()
    patch.to_csv(args.patch_out, index=False)
    print(f"\n2025-26 季后赛 (ESPN): {len(patch)} 名球员 -> {args.patch_out}")
    print(patch[["player", "GP", "MIN", "PPG", "APG", "RPG"]].sort_values("GP", ascending=False).to_string(index=False))
    return 0 if len(mm) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
