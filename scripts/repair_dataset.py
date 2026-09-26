"""
数据集修复 (幂等, 可重复运行)

修复两个已确认的问题:
  A. 多队赛季三重计算
     stats.nba.com 对"赛季中换队"的球员同时返回 球队A / 球队B / TOT 三行,
     原始抓取脚本把它们当作 3 个独立赛季。影响 30 名球员 / 41 个赛季:
     巅峰5年会被同一赛季占多个名额, GP 求和后超过 82 场, 时代 Z-score 样本被污染。
     修复: 多队赛季只保留合并行 (TOT)。

  B. 2025-26 赛季不完整
     常规赛快照停在赛季结束前 6-8 场, 且整个 2025-26 季后赛缺失。
     修复: 常规赛用 Basketball-Reference 补齐, 季后赛用 ESPN 逐场数据补齐
     (这两个来源的数据已在 scripts/verify_*.py 中交叉验证过)。

用法:
  python scripts/repair_dataset.py --step dedupe          # 修复 A
  python scripts/repair_dataset.py --step patch-current   # 修复 B
  python scripts/repair_dataset.py --step all
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CURRENT_SEASON = "2025-26"
CURRENT_END_YEAR = 2026

# Basketball-Reference 与 NBA.com 的球队代码差异 (仅本项目出现的)
BREf_TO_NBA = {
    "PHO": "PHX", "BRK": "BKN", "CHO": "CHA", "CHH": "CHH", "NOH": "NOH",
    "NOK": "NOK", "SEA": "SEA", "WSB": "WSB", "CAP": "CAP", "SDC": "SDC",
    "KCK": "KCK", "KCO": "KCO", "SDR": "SDR", "SFW": "SFW", "PHW": "PHW",
    "MLH": "MLH", "TRI": "TRI", "AND": "AND", "DNY": "DNY", "SYR": "SYR",
    "STL": "STL", "ROC": "ROC", "FTW": "FTW", "BAL": "BAL", "CHZ": "CHZ",
    "NYN": "NYN", "BLB": "BLB", "INJ": "INJ", "DET": "DET", "PRO": "PRO",
    "MLH2": "MLH",
}
EXTRA_NAMES = {"jimmy butler": ["jimmy butler iii"], "nate archibald": ["tiny archibald"]}


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


def end_year_to_season(y: int) -> str:
    return f"{y - 1}-{str(y)[2:]}"


def ts_pct(ppg, fga, fta):
    denom = 2 * (fga + 0.44 * fta)
    return round(ppg / denom, 4) if denom else None


# ══════════════════════════════════════════════
# A. 多队赛季去重
# ══════════════════════════════════════════════
def dedupe() -> None:
    print("=" * 72)
    print("A. 多队赛季去重")
    print("=" * 72)

    for fname, has_team in [("nba100_career_all.csv", True), ("nba100_rebounds.csv", False)]:
        path = DATA / fname
        df = pd.read_csv(path)
        before = len(df)
        df["end_year"] = df["season"].map(to_end_year)

        if has_team:
            df["is_total"] = df["team"].astype(str).str.upper().str.fullmatch(r"\d*TOT").fillna(False)
            sizes = df.groupby(["player", "end_year"])["team"].transform("size")
            groups = df[sizes > 1].groupby(["player", "end_year"])
            n_groups = groups.ngroups
            kept = df[sizes == 1].copy()
            for (p, y), g in groups:
                tot = g[g["is_total"]]
                assert len(tot) == 1, f"{p} {y}: TOT 行数 = {len(tot)}"
                teams = g[~g["is_total"]]
                assert int(teams["GP"].sum()) == int(tot.iloc[0]["GP"]), \
                    f"{p} {y}: 分队 GP 之和 {int(teams['GP'].sum())} != TOT GP {int(tot.iloc[0]['GP'])}"
                kept = pd.concat([kept, tot], ignore_index=True)
            out = kept.sort_values(["player", "end_year"]).drop(columns=["end_year", "is_total"])
            assert out.duplicated(["player", "season"]).sum() == 0
            assert (out.groupby(["player", "season"])["GP"].sum() > 82).sum() == 0
        else:
            # 篮板文件没有 team 列, 但每个多队赛季也是 3 行 (2 个分队 + 1 个合并行)。
            # 用自洽规则识别合并行: 它的 GP 等于其余各行 GP 之和 (分队 GP 相加 = 总 GP)
            keep_idx = []
            n_groups = 0
            for (p, y), g in df.groupby(["player", "end_year"]):
                gps = g["GP"].astype(float).tolist()
                if len(gps) == 1:
                    keep_idx.append(g.index[0])
                    continue
                n_groups += 1
                hits = [i for i, gp in enumerate(gps) if abs(gp - (sum(gps) - gp)) < 1e-9]
                assert len(hits) == 1, f"{p} {y}: 无法唯一识别合并行 (GP={gps})"
                keep_idx.append(g.index[hits[0]])
            out = df.loc[keep_idx].sort_values(["player", "end_year"]).drop(columns=["end_year"])
            assert out.duplicated(["player", "season"]).sum() == 0
            assert len(out) == len(df) - 2 * n_groups

        out.to_csv(path, index=False)
        print(f"  {fname:26s} {before} -> {len(out)} 行  (合并 {n_groups} 个多队赛季,"
              f" 删除 {before - len(out)} 行)")

    print("\n  校验: 多队赛季仅保留合并行, GP<=82, 无重复 (player,season)  ✓")


# ══════════════════════════════════════════════
# B. 补齐当前赛季
# ══════════════════════════════════════════════
def load_bref_season(ref_dir: Path, end_year: int) -> pd.DataFrame:
    ref = pd.read_csv(ref_dir / "Player Per Game.csv")
    ref = ref[ref["lg"].isin(["NBA", "BAA"]) & (ref["season"] == end_year)].copy()
    ref["norm"] = ref["player"].map(normalize)
    return ref


def patch_current(ref_dir: Path, espn_cache: Path) -> None:
    print("=" * 72)
    print(f"B. 补齐 {CURRENT_SEASON} 赛季")
    print("=" * 72)

    career_path = DATA / "nba100_career_all.csv"
    po_path = DATA / "nba100_playoffs.csv"
    career = pd.read_csv(career_path)
    po = pd.read_csv(po_path)

    # ── B1. 常规赛 (Basketball-Reference) ──
    ref = load_bref_season(ref_dir, CURRENT_END_YEAR)
    cur_players = sorted(career[career["season"] == CURRENT_SEASON]["player"].unique())
    print(f"  常规赛: 本地有 {len(cur_players)} 名球员的 {CURRENT_SEASON} 数据")

    field_map = {
        "GP": "g", "GS": "gs", "MIN": "mp_per_game", "PPG": "pts_per_game",
        "RPG": "trb_per_game", "APG": "ast_per_game", "SPG": "stl_per_game",
        "BPG": "blk_per_game", "TOV": "tov_per_game", "FGM": "fg_per_game",
        "FGA": "fga_per_game", "FG_PCT": "fg_percent", "FG3M": "x3p_per_game",
        "FG3A": "x3pa_per_game", "FG3_PCT": "x3p_percent", "FTM": "ft_per_game",
        "FTA": "fta_per_game", "FT_PCT": "ft_percent", "age": "age",
    }
    replaced, added = 0, 0
    gp_before = int(career[career["season"] == CURRENT_SEASON]["GP"].sum())
    for player in cur_players:
        r = ref[ref["norm"].isin(name_keys(player))]
        # 多队赛季取合并行 (B-R 用 2TM/3TM)
        if len(r) > 1:
            agg = r[r["team"].astype(str).str.fullmatch(r"\d+TM")]
            assert len(agg) == 1, f"{player}: B-R 多队合并行数 = {len(agg)}"
            r = agg
        assert len(r) == 1, f"{player}: B-R {CURRENT_SEASON} 行数 = {len(r)}"
        r = r.iloc[0]

        new = {
            "player": player,
            "nba_id": int(career.loc[career["player"] == player, "nba_id"].iloc[0]),
            "season": CURRENT_SEASON,
            "team": BREf_TO_NBA.get(str(r["team"]), str(r["team"])) if not str(r["team"]).endswith("TM") else "TOT",
        }
        for ours_col, ref_col in field_map.items():
            new[ours_col] = r[ref_col]
        new["TS_pct"] = ts_pct(new["PPG"], new["FGA"], new["FTA"])

        old = career[(career["player"] == player) & (career["season"] == CURRENT_SEASON)]
        assert len(old) == 1, f"{player}: 去重后本地 {CURRENT_SEASON} 行数 = {len(old)} (应先运行 dedupe)"
        assert float(new["GP"]) >= float(old.iloc[0]["GP"]), \
            f"{player}: 补齐后 GP {new['GP']} < 原 {old.iloc[0]['GP']}"
        career = career.drop(old.index)
        career = pd.concat([career, pd.DataFrame([new])], ignore_index=True)
        replaced += 1

    # 池内是否有球员打了 2025-26 但本地完全没有 (漏赛季)
    career_norms = {normalize(p) for p in career["player"].unique()}
    missing = ref[ref["norm"].isin(career_norms)]
    if len(missing):
        for _, r in missing.iterrows():
            owner = [p for p in career["player"].unique() if normalize(p) == r["norm"]]
            if owner and not ((career["player"] == owner[0]) & (career["season"] == CURRENT_SEASON)).any():
                print(f"    ! {owner[0]} 有 {CURRENT_SEASON} 数据但本地缺失, 已新增")
                added += 1

    career = career.sort_values(["player", "season"]).reset_index(drop=True)
    career.to_csv(career_path, index=False)
    gp_after = int(career[career["season"] == CURRENT_SEASON]["GP"].sum())
    print(f"  常规赛: 更新 {replaced} 行 (来源: Basketball-Reference), 新增 {added} 行")
    print(f"          {CURRENT_SEASON} 总出场数 {gp_before} -> {gp_after} 场")

    # ── B1b. 篮板 (同一来源, 保持三个文件对 2025-26 的口径一致) ──
    reb_path = DATA / "nba100_rebounds.csv"
    reb = pd.read_csv(reb_path)
    reb_cols = ["player", "season", "OREB", "DREB", "REB", "GP", "MIN"]
    reb_players = reb[reb["season"] == CURRENT_SEASON]["player"].unique()
    n_reb = 0
    for player in reb_players:
        r = ref[ref["norm"].isin(name_keys(player))]
        if len(r) > 1:
            r = r[r["team"].astype(str).str.fullmatch(r"\d+TM")]
        assert len(r) == 1, f"{player}: B-R {CURRENT_SEASON} 篮板行数 = {len(r)}"
        r = r.iloc[0]
        old = reb[(reb["player"] == player) & (reb["season"] == CURRENT_SEASON)]
        row = {"player": player, "season": CURRENT_SEASON,
               "OREB": r["orb_per_game"], "DREB": r["drb_per_game"], "REB": r["trb_per_game"],
               "GP": r["g"], "MIN": r["mp_per_game"]}
        reb = reb.drop(old.index)
        reb = pd.concat([reb, pd.DataFrame([row])], ignore_index=True)
        n_reb += 1
    reb = reb[reb_cols].sort_values(["player", "season"]).reset_index(drop=True)
    assert reb.duplicated(["player", "season"]).sum() == 0
    reb.to_csv(reb_path, index=False)
    print(f"  篮板:   更新 {n_reb} 行 (来源: Basketball-Reference)")

    # ── B2. 季后赛 (ESPN) ──
    patch_file = espn_cache / "playoffs_2026.csv"
    if not patch_file.exists():
        print(f"  季后赛: 缺少 {patch_file}, 跳过 (先运行 scripts/verify_playoffs_espn.py)")
        return
    esp = pd.read_csv(patch_file)
    if "our_player" in esp.columns:
        esp["player"] = esp["our_player"]

    ids = pd.read_json(DATA / "nba100_ids.json", typ="series").to_dict()
    id_by_name = {v: int(k) for k, v in ids.items()}

    known = set(po["player"])
    existing = set(po[po["season"] == CURRENT_SEASON]["player"])
    rows = []
    for _, r in esp.iterrows():
        if r["player"] not in known or r["player"] in existing:
            continue
        rows.append({
            "player": r["player"], "nba_id": id_by_name[r["player"]], "season": CURRENT_SEASON,
            "GP": int(r["GP"]), "MIN": r["MIN"], "PPG": r["PPG"], "APG": r["APG"], "RPG": r["RPG"],
            "FGM": r["FGM"], "FGA": r["FGA"], "FTM": r["FTM"], "FTA": r["FTA"],
            "TS_pct": ts_pct(r["PPG"], r["FGA"], r["FTA"]),
        })
    if rows:
        po = pd.concat([po, pd.DataFrame(rows)], ignore_index=True)
    po["_y"] = po["season"].map(to_end_year)
    po = po.sort_values(["player", "_y"]).drop(columns="_y").reset_index(drop=True)
    po.to_csv(po_path, index=False)
    print(f"  季后赛: 新增 {len(rows)} 行 (来源: ESPN/hoopR) -> {', '.join(r['player'] for r in rows)}")
    print(f"          季后赛赛季范围: {po['season'].min()} → {po['season'].max()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["dedupe", "patch-current", "all"], default="all")
    ap.add_argument("--ref-dir", default="/tmp/nba_verify")
    ap.add_argument("--espn-cache", default="/tmp/nba_verify")
    args = ap.parse_args()

    if args.step in ("dedupe", "all"):
        dedupe()
        print()
    if args.step in ("patch-current", "all"):
        patch_current(Path(args.ref_dir), Path(args.espn_cache))
    print("\n完成。请重新运行校验:")
    print("  python scripts/verify_reference_data.py --ref-dir /tmp/nba_verify")
    print("  python scripts/verify_playoffs_espn.py --cache /tmp/nba_verify/hoopr")
    return 0


if __name__ == "__main__":
    sys.exit(main())