"""仪表盘的数据装配。

单独抽出来是为了可测试 —— app.py 一旦执行就会跑 Streamlit 命令,
没法在测试里 import。这里的合并顺序和列名冲突曾经导致过 KeyError
(def_rank 同时来自 all_rankings.csv 和 defense_ranking.csv, 合并后变成
def_rank_x / def_rank_y), 所以有 test_dashboard_data.py 专门盯住。
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# 仪表盘需要的名次列 —— 只从 all_rankings.csv 取, 避免和维度明细表重复合并
RANK_COLUMNS = ["scoring_rank", "impact_rank", "play_rank", "def_rank", "reb_rank"]


def build_career_frame(data_dir: Path, results_dir: Path) -> pd.DataFrame:
    reg = pd.read_csv(data_dir / "nba100_career_all.csv")
    po = pd.read_csv(data_dir / "nba100_playoffs.csv")
    ranks = pd.read_csv(results_dir / "all_rankings.csv")
    rebounding = pd.read_csv(results_dir / "rebounding_ranking.csv")

    career = reg.groupby("player").agg({
        "PPG": "mean", "FGM": "mean", "FG3M": "mean",
        "FTM": "mean", "TS_pct": "mean", "GP": "sum",
        "APG": "mean", "MIN": "mean",
        "TOV": "mean",
    }).round(3).reset_index()
    career["FG3M"] = career["FG3M"].fillna(0)
    career["FG2M"] = career["FGM"] - career["FG3M"]
    career["pts_2P"] = career["FG2M"] * 2
    career["pts_3P"] = career["FG3M"] * 3
    career["pts_FT"] = career["FTM"]
    career["pts_total"] = career["pts_2P"] + career["pts_3P"] + career["pts_FT"]
    career["pct_2P"] = (career["pts_2P"] / career["pts_total"] * 100).round(1)
    career["pct_3P"] = (career["pts_3P"] / career["pts_total"] * 100).round(1)
    career["pct_FT"] = (career["pts_FT"] / career["pts_total"] * 100).round(1)
    career["purity"] = (100 - career["pct_FT"]).round(1)
    # 助失比只在有失误记录时才算。1977-78 之前没有 TOV, 用常数伪造会
    # 让早期球员的助失比全部等于 APG/2.5, 是个假指标, 所以保留缺失。
    career["ast_tov"] = (career["APG"] / career["TOV"]).round(2)

    po_avg = po.groupby("player").agg({"PPG": "mean", "APG": "mean", "GP": "sum"}).round(2).reset_index()
    po_avg.columns = ["player", "po_PPG", "po_APG", "po_GP"]
    career = career.merge(po_avg, on="player", how="left")
    career["po_delta"] = (career["po_PPG"] - career["PPG"]).round(2)

    career = career.merge(ranks[["player"] + RANK_COLUMNS], on="player", how="left")
    # 篮板明细只在 total rebounding 之外补 RPG/OREB/DREB 三列; 名次一律用 all_rankings
    career = career.merge(
        rebounding[["player", "RPG", "OREB", "DREB"]].rename(
            columns={"RPG": "reb_RPG", "OREB": "reb_OREB", "DREB": "reb_DREB"}),
        on="player", how="left")
    return career


def load_dimension(results_dir: Path, fname: str) -> pd.DataFrame:
    """单个维度的明细表 (含图表要用的列)"""
    return pd.read_csv(results_dir / fname)
