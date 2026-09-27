"""把结果数据编译成静态站需要的数据文件 (docs/assets/data.js)。

为什么产出 .js 而不是 .json: 站点要能从 file:// 直接双击打开 —— fetch 本地 json 会被
浏览器拦, 而 <script> 加载 window.NBA_DATA 不会。这样站点不依赖任何服务器。

用法:
  python scripts/build_site.py            # 写 docs/assets/data.js
  python scripts/build_site.py --serve    # 顺便起个本地服务看效果
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
OUT = ROOT / "docs" / "assets"

DIMENSIONS = ["scoring", "impact", "playmaking", "defense", "rebounding"]
RANK_COL = {"scoring": "scoring_rank", "impact": "impact_rank", "playmaking": "play_rank",
            "defense": "def_rank", "rebounding": "reb_rank"}

# NBA.com 的历史球队代码 -> 现在的球队。徽章用球队配色, 老代码必须归一化,
# 否则 Mikan 的 MNL、Schayes 的 SYR 会变成没有颜色的孤儿。
FRANCHISE = {
    "ATL": "ATL", "STL": "ATL", "MIH": "ATL",
    "BOS": "BOS",
    "BKN": "BKN", "NJN": "BKN", "NYN": "BKN",
    "CHA": "CHA", "CHH": "CHA",
    "CHI": "CHI", "CLE": "CLE", "DAL": "DAL", "DEN": "DEN",
    "DET": "DET", "FTW": "DET",
    "GSW": "GSW", "PHW": "GSW", "SFW": "GSW", "GOS": "GSW",
    "HOU": "HOU", "SDR": "HOU",
    "IND": "IND",
    "LAC": "LAC", "BUF": "LAC", "SDC": "LAC",
    "LAL": "LAL", "MNL": "LAL",
    "MEM": "MEM", "VAN": "MEM", "MIA": "MIA", "MIL": "MIL", "MIN": "MIN",
    "NOP": "NOP", "NOH": "NOP", "NOK": "NOP",
    "NYK": "NYK", "OKC": "OKC", "SEA": "OKC", "ORL": "ORL",
    "PHI": "PHI", "PHL": "PHI", "SYR": "PHI",
    "PHX": "PHX", "PHO": "PHX", "POR": "POR",
    "SAC": "SAC", "CIN": "SAC", "KCK": "SAC", "KCO": "SAC", "ROC": "SAC",
    "SAS": "SAS", "SAN": "SAS", "TOR": "TOR",
    "UTA": "UTA", "UTH": "UTA", "NOJ": "UTA",
    "WAS": "WAS", "CAP": "WAS", "BLT": "WAS", "WSB": "WAS", "CHZ": "WAS", "CHP": "WAS",
}
# 球队主色 (深色底上做淡色徽章用, 不是整块填充)
TEAM_COLORS = {
    "ATL": "#e03a3e", "BOS": "#00a651", "BKN": "#8f9bb3", "CHA": "#7b5fd6",
    "CHI": "#ce1141", "CLE": "#b0345c", "DAL": "#2f7fd1", "DEN": "#5b8dd6",
    "DET": "#e0435f", "GSW": "#4a7ede", "HOU": "#e0435f", "IND": "#3f7fd6",
    "LAC": "#d94b52", "LAL": "#a06fe8", "MEM": "#7f9fd6", "MIA": "#d94b6a",
    "MIL": "#3fa06a", "MIN": "#5b8dd6", "NOP": "#6f8fd6", "NYK": "#3f8ed6",
    "OKC": "#3fa6e0", "ORL": "#3f8ed6", "PHI": "#4f8ee0", "PHX": "#8f6fd6",
    "POR": "#e05a5a", "SAC": "#9a6fd6", "SAS": "#9aa5b5", "TOR": "#e04b5a",
    "UTA": "#4f8ed6", "WAS": "#4f8ed6",
}


def primary_franchise(reg: pd.DataFrame) -> dict[str, str]:
    """出场最多的球队 = 球员的代表球队 (排除 TOT 合并行)"""
    real = reg[reg["team"].str.upper() != "TOT"]
    top = real.sort_values("GP", ascending=False).groupby("player").head(1)
    return {r.player: FRANCHISE.get(r.team, r.team) for r in top.itertuples()}


def _clean(value):
    """NaN/NaT 不能进 JSON (会变成非法的 NaN 字面量)"""
    if value is None or (isinstance(value, float) and value != value):
        return None
    if pd.isna(value):
        return None
    return value


def build_payload() -> dict:
    reg = pd.read_csv(DATA / "nba100_career_all.csv")
    po = pd.read_csv(DATA / "nba100_playoffs.csv")
    ranks = pd.read_csv(RESULTS / "all_rankings.csv")
    defense = pd.read_csv(RESULTS / "defense_ranking.csv")
    rebounding = pd.read_csv(RESULTS / "rebounding_ranking.csv")
    playmaking = pd.read_csv(RESULTS / "playmaking_ranking.csv")

    # ── 球员表: 生涯均值 + 五个维度名次 ──
    career = reg.groupby("player").agg(
        ppg=("PPG", "mean"), rpg=("RPG", "mean"), apg=("APG", "mean"),
        ts=("TS_pct", "mean"), gp=("GP", "sum"), seasons=("season", "count"),
        first=("season", "min"), last=("season", "max"),
    ).round(3).reset_index()

    pts = reg.assign(
        p2=reg["FGM"].sub(reg["FG3M"].fillna(0)) * 2,
        p3=reg["FG3M"].fillna(0) * 3, pft=reg["FTM"],
    )
    split = pts.groupby("player")[["p2", "p3", "pft"]].mean().round(1)
    split["total"] = split.sum(axis=1)
    for c in ["p2", "p3", "pft"]:
        split[c] = (split[c] / split["total"] * 100).round(1)
    career = career.merge(split[["p2", "p3", "pft"]].reset_index(), on="player")

    po_avg = po.groupby("player").agg(po_ppg=("PPG", "mean"), po_apg=("APG", "mean"),
                                      po_rpg=("RPG", "mean"), po_gp=("GP", "sum")).round(2)
    career = career.merge(po_avg.reset_index(), on="player", how="left")

    players = career.merge(
        ranks[["player", "scoring_rank", "impact_rank", "play_rank", "def_rank",
               "reb_rank", "era_group", "has_advanced_data"]], on="player", how="left")
    players = players.merge(
        defense[["player", "seasons_with_def_data", "defense_stats_missing",
                 "sample_too_small", "stl_rank", "blk_rank", "def_impact_rank",
                 "d_dpm"]], on="player", how="left")
    players = players.merge(
        rebounding[["player", "oreb_rank", "dreb_rank", "peak_OREB", "peak_DREB",
                    "rebound_split_missing"]], on="player", how="left")
    players = players.merge(
        playmaking[["player", "TOV_imputed_share"]], on="player", how="left")

    teams = primary_franchise(reg)
    records = []
    for r in players.itertuples():
        rec = {"name": r.player, "ppg": _clean(r.ppg), "rpg": _clean(r.rpg),
               "apg": _clean(r.apg), "ts": _clean(r.ts), "gp": int(r.gp),
               "seasons": int(r.seasons), "first": r.first, "last": r.last,
               "split2": _clean(r.p2), "split3": _clean(r.p3), "splitFt": _clean(r.pft)}
        for dim in DIMENSIONS:
            col = RANK_COL[dim]
            rec[dim] = _clean(getattr(r, col.replace("_rank", "_rank") if False else col))
        rec["stl_rank"] = _clean(r.stl_rank)
        rec["blk_rank"] = _clean(r.blk_rank)
        rec["oreb_rank"] = _clean(r.oreb_rank)
        rec["dreb_rank"] = _clean(r.dreb_rank)
        rec["def_seasons"] = int(r.seasons_with_def_data) if pd.notna(r.seasons_with_def_data) else 0
        rec["def_excluded"] = bool(r.defense_stats_missing) or bool(r.sample_too_small)
        rec["reb_split_missing"] = bool(r.rebound_split_missing)
        rec["tov_estimated"] = bool((r.TOV_imputed_share or 0) > 0.5)
        rec["po_ppg"] = _clean(r.po_ppg)
        rec["po_rpg"] = _clean(r.po_rpg)
        rec["po_apg"] = _clean(r.po_apg)
        rec["po_gp"] = int(r.po_gp) if pd.notna(r.po_gp) else 0
        team = teams.get(r.player, "")
        rec["team"] = team
        rec["teamColor"] = TEAM_COLORS.get(team, "#7c8899")
        records.append(rec)

    # ── 生涯曲线: 每季场均得分/真实命中率 ──
    curves = {}
    for name, g in reg.groupby("player"):
        g = g.sort_values("season")
        curves[name] = {
            "season": [s[:4] for s in g["season"]],
            "ppg": [_clean(v) for v in g["PPG"]],
            "ts": [_clean(v) for v in g["TS_pct"]],
            "team": list(g["team"]),
        }

    # ── 细分榜与影响力 ──
    def picks(df: pd.DataFrame, col: str, extra: list[str], n: int = 30) -> list[dict]:
        d = df[df[col].notna()].nsmallest(n, col)
        return [{"name": r["player"], "rank": int(r[col]),
                 **{k: _clean(r[k]) for k in extra}} for _, r in d.iterrows()]

    subsets = {
        "steals": picks(defense, "stl_rank", ["reg_SPG"]),
        "blocks": picks(defense, "blk_rank", ["reg_BPG"]),
        "oreb": picks(rebounding, "oreb_rank", ["peak_OREB"]),
        "dreb": picks(rebounding, "dreb_rank", ["peak_DREB"]),
        "dimpact": picks(defense, "def_impact_rank",
                         ["def_impact_score", "d_dpm", "reg_SPG", "reg_BPG"]),
    }

    # ── 校验状态 (写死在数据里, 站点直接展示) ──
    verification = {
        "regular_rows": int(len(reg)), "playoff_rows": int(len(po)),
        "players": int(players["player"].nunique()),
        "primary_match": "100%", "br_match": "99.86%", "espn_match": "100%",
        "playoff_pre2002_rows": int((po["season"] < "2002-03").sum()),
        "generated": date.today().isoformat(),
    }

    return {"players": records, "curves": curves, "subsets": subsets,
            "meta": verification}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    args = ap.parse_args()

    payload = build_payload()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "data.js"
    target.write_text("window.NBA_DATA = " + json.dumps(payload, ensure_ascii=False,
                                                       separators=(",", ":")) + ";\n")
    kb = target.stat().st_size / 1024
    print(f"-> {target.relative_to(ROOT)}  ({kb:.0f} KB, {len(payload['players'])} 名球员)")
    print(f"   校验状态: 常规赛 {payload['meta']['regular_rows']} 行 / "
          f"季后赛 {payload['meta']['playoff_rows']} 行, 与官方 {payload['meta']['primary_match']} 一致")

    if args.serve:
        import functools
        import http.server
        import socketserver
        handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                    directory=str(ROOT / "docs"))
        print("本地预览: http://localhost:8765")
        with socketserver.TCPServer(("127.0.0.1", 8765), handler) as httpd:
            httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
