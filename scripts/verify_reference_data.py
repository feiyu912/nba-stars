"""
数据校验: 把 data/nba100_*.csv 与独立的 Basketball-Reference 数据集逐季比对

为什么需要它:
  data/nba100_career_all.csv 的原始抓取脚本无脑遍历了 nba_api 返回的所有行,
  而 stats.nba.com 对"赛季中换队"的球员会同时返回 球队A / 球队B / TOT 三行。
  这导致 30 名球员的 41 个赛季被三重计算 (巅峰取5年、GP求和、时代Z-score全部受影响)。

参考数据 (Basketball-Reference 派生, 覆盖 NBA+BAA+ABA 1947-至今):
  https://github.com/sumitrodatta/bball-reference-datasets  (branch: master, Data/)
  需要: "Player Per Game.csv"  "Player Totals.csv"

用法:
  python scripts/verify_reference_data.py --ref-dir /tmp/nba_verify
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# NBA.com 与 B-R 两边都是 1 位小数, 各队行求和存在舍入差, 故给容差
TOL = 0.15
FIELDS = {
    "GP": ("g", 0.0),
    "MIN": ("mp_per_game", TOL),
    "PPG": ("pts_per_game", TOL),
    "RPG": ("trb_per_game", TOL),
    "APG": ("ast_per_game", TOL),
    "FGM": ("fg_per_game", TOL),
    "FGA": ("fga_per_game", TOL),
    "FTM": ("ft_per_game", TOL),
    "FTA": ("fta_per_game", TOL),
}
REB_FIELDS = {"RPG": ("trb_per_game", TOL), "OREB": ("orb_per_game", TOL), "DREB": ("drb_per_game", TOL)}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
# B-R 用绰号/别名收录的球员
ALIASES = {"Nate Archibald": "Tiny Archibald"}
# 参考数据只保留 NBA + BAA (ABA 不在本项目的统计范围内)
LEAGUES = {"NBA", "BAA"}
CURRENT_SEASON_START = 2025  # 2025-26: 本地快照不完整, 单独归类


def normalize(name: str) -> str:
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower().replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(p for p in n.split() if p not in SUFFIXES)


def to_end_year(season: str) -> int:
    return int(str(season)[:4]) + 1


def load_ours() -> pd.DataFrame:
    df = pd.read_csv(DATA / "nba100_career_all.csv")
    df["end_year"] = df["season"].map(to_end_year)
    df["is_total"] = df["team"].astype(str).str.upper().str.fullmatch(r"\d*TOT").fillna(False)
    return df


def load_ref(ref_dir: Path) -> pd.DataFrame:
    ref = pd.read_csv(ref_dir / "Player Per Game.csv")
    ref = ref[ref["lg"].isin(LEAGUES)].copy()
    ref["season"] = ref["season"].astype(int)
    ref["is_total"] = ref["team"].astype(str).str.fullmatch(r"\d+TM").fillna(False)
    ref["norm"] = ref["player"].map(lambda p: normalize(ALIASES.get(p, p)))
    return ref


def resolve_ref(group: pd.DataFrame, ours_seasons: set[int]) -> pd.DataFrame | None:
    """同一归一化名字可能对应多个人 (Gary Payton / Gary Payton II)，按赛季重叠取最匹配的一个"""
    if group["player_id"].nunique() == 1:
        return group
    best, best_ov = None, -1
    for _, g in group.groupby("player_id"):
        ov = len(set(g["season"]) & ours_seasons)
        if ov > best_ov:
            best, best_ov = g, ov
    return best


def pick(group_ours: pd.DataFrame, group_ref: pd.DataFrame):
    o = group_ours[group_ours["is_total"]] if len(group_ours) > 1 else group_ours
    r = group_ref[group_ref["is_total"]] if len(group_ref) > 1 else group_ref
    return o, r


def compare(ours, ref, fields, prefix="") -> tuple[list[dict], list[dict], int]:
    ref_index: dict[str, pd.DataFrame] = {n: g for n, g in ref.groupby("norm")}
    mismatches, missing = [], []
    checked = 0
    for player in sorted(ours["player"].unique()):
        g_ours_all = ours[ours["player"] == player]
        ours_seasons = set(g_ours_all["end_year"])
        g_ref_all = ref_index.get(normalize(ALIASES.get(player, player)))
        if g_ref_all is None:
            missing.append({"player": player, "reason": "参考数据中无此人"})
            continue
        g_ref_all = resolve_ref(g_ref_all, ours_seasons)
        ref_seasons = set(g_ref_all["season"])
        for s in sorted(ours_seasons - ref_seasons):
            missing.append({"player": player, "end_year": s, "reason": "参考数据缺失该赛季"})
        for end_year, g_ours in g_ours_all.groupby("end_year"):
            g_ref = g_ref_all[g_ref_all["season"] == end_year]
            if g_ref.empty:
                continue
            o, r = pick(g_ours, g_ref)
            if len(o) != 1 or len(r) != 1:
                mismatches.append({"player": player, "season": o["season"].iloc[0], "field": "(结构)",
                                   "ours": f"{len(o)}行", "ref": f"{len(r)}行", "kind": "structure"})
                continue
            checked += 1
            o_row, r_row = o.iloc[0], r.iloc[0]
            for ours_col, (ref_col, tol) in fields.items():
                ov, rv = o_row.get(ours_col), r_row.get(ref_col)
                if pd.isna(ov) and pd.isna(rv):
                    continue
                if pd.isna(ov) or pd.isna(rv):
                    mismatches.append({"player": player, "season": o_row["season"], "field": f"{prefix}{ours_col}",
                                       "ours": ov, "ref": rv, "delta": None, "kind": "one-side-null"})
                    continue
                d = abs(float(ov) - float(rv))
                if d > tol:
                    mismatches.append({"player": player, "season": o_row["season"], "field": f"{prefix}{ours_col}",
                                       "ours": ov, "ref": rv, "delta": round(d, 3), "kind": "value"})
    return mismatches, missing, checked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-dir", default="/tmp/nba_verify")
    ap.add_argument("--detail-out", default="/tmp/nba_verify/mismatches.csv")
    args = ap.parse_args()
    ref_dir = Path(args.ref_dir)
    if not (ref_dir / "Player Per Game.csv").exists():
        print(f"缺少参考数据: {ref_dir / 'Player Per Game.csv'}")
        return 2

    ours, ref = load_ours(), load_ref(ref_dir)
    print("=" * 80)
    print("数据校验: data/nba100_career_all.csv  vs  Basketball-Reference (独立数据源)")
    print("=" * 80)
    print(f"本地: {len(ours)} 行 / {ours['player'].nunique()} 人     参考: {len(ref)} 行 / {ref['player_id'].nunique()} 人")
    print(f"容差: GP 精确, 其余 ±{TOL} (两边各 1 位小数)")

    mismatches, missing, checked = compare(ours, ref, FIELDS)
    print(f"\n已逐季核对 {checked} 个球员赛季")

    if missing:
        print(f"\n-- 覆盖差异 ({len(missing)}) --")
        for m in missing:
            print(f"   {m['player']:26s} {m.get('end_year','')}  {m['reason']}")

    if mismatches:
        mm = pd.DataFrame(mismatches)
        mm["cur"] = mm["season"].str[:4].astype(int) >= CURRENT_SEASON_START
        pd.DataFrame(mismatches).to_csv(args.detail_out, index=False)
        cur, hist = mm[mm["cur"]], mm[~mm["cur"]]
        print(f"\n-- 数值不符: 共 {len(mm)} 处 --")
        print(f"   其中当季快照不完整 ({CURRENT_SEASON_START}-{str(CURRENT_SEASON_START + 1)[2:]}): {len(cur)} 处")
        print(f"   历史赛季: {len(hist)} 处")
        if len(hist):
            print("\n   历史赛季差异明细:")
            print(hist[["player", "season", "field", "ours", "ref", "delta"]].to_string(index=False))
        print(f"\n   明细已写入 {args.detail_out}")
    else:
        print("\n-- 无数值不符 --")

    # ── 附加: 篮板文件 ──
    reb_path = DATA / "nba100_rebounds.csv"
    if reb_path.exists():
        reb = pd.read_csv(reb_path)
        reb["end_year"] = reb["season"].map(to_end_year)
        dups = reb.duplicated(["player", "season"]).sum()
        # 篮板文件没有 team 列, 用 GP 把每行对齐到 career 的合并行, 从而剔除分队行
        kept = ours[(ours.groupby(["player", "end_year"])["team"].transform("size") == 1) | ours["is_total"]]
        tot_gp = kept[["player", "end_year", "GP"]].rename(columns={"GP": "gp_tot"})
        reb_tot = reb.merge(tot_gp, on=["player", "end_year"], how="left")
        reb_tot = reb_tot[reb_tot["GP"] == reb_tot["gp_tot"]].rename(columns={"REB": "RPG"})
        # base 只保留键列, 避免与 career 的 RPG/GP 同名冲突
        base = kept[["player", "season", "end_year", "team", "is_total"]]
        r_ours = base.merge(reb_tot[["player", "end_year", "RPG", "OREB", "DREB"]],
                            on=["player", "end_year"], how="left")
        print(f"\n-- 篮板文件: {len(reb)} 行, 重复 (player,season) {dups} 处, "
              f"对齐到合并行后 {len(reb_tot)} 行 --")
        rm, _, rchecked = compare(r_ours, ref, REB_FIELDS)
        rmm = pd.DataFrame(rm)
        if len(rmm):
            rmm["cur"] = rmm["season"].str[:4].astype(int) >= CURRENT_SEASON_START
            h = rmm[~rmm["cur"]]
            print(f"   已核对 {rchecked} 个球员赛季, 数值不符 {len(rmm)} 处 "
                  f"(历史 {len(h)} / 当季 {len(rmm) - len(h)})")
            if len(h):
                print(h[["player", "season", "field", "ours", "ref", "delta"]].head(30).to_string(index=False))
        else:
            print(f"   已核对 {rchecked} 个球员赛季, 数值不符 0 处")

    hist_total = len([m for m in mismatches if int(str(m["season"])[:4]) < CURRENT_SEASON_START])
    ok = checked - len({(m["player"], m["season"]) for m in mismatches if int(str(m["season"])[:4]) < CURRENT_SEASON_START})
    print("\n" + "=" * 80)
    if checked:
        print(f"历史赛季一致性: {ok}/{checked} = {ok / checked * 100:.2f}%  (不含 {CURRENT_SEASON_START}-26 当季)")
    return 0 if hist_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())