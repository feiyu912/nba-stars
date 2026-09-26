"""四个维度的指标构造 (原先各自散落在 05/08/09/10 里)。

每个维度 = 两个视角:
  A 视角: 产量 × 效率 × 稀缺性 (pace 修正)
  C 视角: 每分钟产出 × 竞争强度 × 稀缺性
两个视角分别排名再取中位数, 是为了避免单一口径 (总量 vs 效率) 决定结果。
"""
from __future__ import annotations

import pandas as pd

from . import config
from .era import add_era_columns, add_scarcity, per_minute


def _base(df: pd.DataFrame, ts_col: str | None) -> pd.DataFrame:
    df = add_era_columns(df)
    if ts_col:
        df["TS_pct"] = df[ts_col]
        df["TS_plus"] = df["TS_pct"] / df["lts"]
    return df


# ── 得分能力 ──
def scoring_views(df: pd.DataFrame, ft_discount: float = config.FT_DISCOUNT) -> pd.DataFrame:
    """A = 罚球折算后的场均得分 × TS+ × 稀缺性; C = 每分钟版本 × 竞争强度"""
    df = _base(df.copy(), "TS_pct")
    df["FT_points"] = df["FTM"]
    df["FG_points"] = df["PPG"] - df["FT_points"]
    df["PPG_adj_ft"] = df["FG_points"] + df["FT_points"] * ft_discount
    df["PPG_adj"] = df["PPG_adj_ft"] * df["pace_adj"]
    df = add_scarcity(df, "PPG")
    df["scoreA"] = df["PPG_adj"] * df["TS_plus"] * df["scarcity"]
    df["scoreC"] = (per_minute(df, "PPG_adj_ft") * df["TS_plus"]
                    * df["competition"] * df["scarcity"])
    return df


SCORING_AGG = {"PPG": "mean", "TS_pct": "mean", "GP": "sum",
               "APG": "mean", "FTM": "mean", "MIN": "mean"}
SCORING_VIEWS = {"A": "scoreA", "C": "scoreC"}


# ── 组织能力 ──
def playmaking_views(df: pd.DataFrame, tov_imputed: float | None = 2.5) -> pd.DataFrame:
    """A = 助攻 × 助失比 × 稀缺性; C = 每分钟助攻版本

    TOV 在 1977-78 之前没有记录。tov_imputed 给定值时用联盟平均填补 (历史遗留做法),
    同时输出 TOV_imputed 标记, 让使用方知道这些赛季的助失比是估算的。
    """
    df = _base(df.copy(), None)
    if "TOV" not in df.columns:
        # 季后赛数据源没有失误列, 只能整列估算 —— 这些赛季的助失比全是估算值
        df["TOV"] = float("nan")
    df["TOV_imputed"] = df["TOV"].isna()
    if tov_imputed is not None:
        df["TOV"] = df["TOV"].fillna(tov_imputed)
    df["TOV"] = df["TOV"].replace(0, 0.5)
    df["ast_tov"] = df["APG"] / df["TOV"]
    df = add_scarcity(df, "APG")
    df["APG_adj"] = df["APG"] * df["pace_adj"]
    df["playA"] = df["APG_adj"] * df["ast_tov"] * df["scarcity"]
    df["playC"] = (per_minute(df, "APG") * df["ast_tov"]
                   * df["competition"] * df["scarcity"])
    return df


PLAYMAKING_AGG = {"APG": "mean", "TOV": "mean", "ast_tov": "mean",
                  "GP": "sum", "MIN": "mean", "TOV_imputed": "mean"}
PLAYMAKING_VIEWS = {"A": "playA", "C": "playC"}


# ── 防守能力 ──
def defense_views(df: pd.DataFrame) -> pd.DataFrame:
    """产出 = STL + BLK (抢断和盖帽是两种技能, 这里等权)

    1973-74 之前没有抢断/盖帽记录 (池内 11 名球员整段生涯缺失)。
    **不做任何填充** —— 填充出来的名次是假的名次, 这些球员在防守维度
    显示 N/A 且不参与排名。缺失就是缺失。
    """
    df = _base(df.copy(), None)
    df["def_output"] = df["SPG"] + df["BPG"]
    df["def_adj"] = df["def_output"] * df["pace_adj"]
    df = add_scarcity(df, "def_output")
    df["defA"] = df["def_adj"] * df["scarcity"]
    df["defC"] = (per_minute(df, "def_output") * df["competition"] * df["scarcity"])
    return df


DEFENSE_AGG = {"SPG": "mean", "BPG": "mean", "def_output": "mean",
               "GP": "sum", "MIN": "mean"}
DEFENSE_VIEWS = {"A": "defA", "C": "defC"}


# ── 篮板能力 ──
def rebounding_views(df: pd.DataFrame) -> pd.DataFrame:
    """总篮板两个视角只用 REB (1950-51 起就有记录)。

    OREB/DREB 拆分在 1973-74 之前不存在, **不做 30/70 估算** ——
    那些球员的进攻/防守篮板专项榜显示 N/A, 但总篮板榜照常参与。
    """
    df = _base(df.copy(), None)
    df["RPG_adj"] = df["REB"] * df["pace_adj"]
    df = add_scarcity(df, "REB")
    df["rebA"] = df["RPG_adj"] * df["scarcity"]
    df["rebC"] = per_minute(df, "REB") * df["competition"] * df["scarcity"]
    return df


REBOUNDING_AGG = {"REB": "mean", "OREB": "mean", "DREB": "mean",
                  "GP": "sum", "MIN": "mean"}
REBOUNDING_VIEWS = {"A": "rebA", "C": "rebC"}


def ft_discount_sensitivity(reg: pd.DataFrame, po: pd.DataFrame,
                            discounts=(0.6, 0.7, 0.8)) -> pd.DataFrame:
    """罚球折算系数敏感性分析: 名次波动多大才算稳健 (原先只做过这一项)"""
    from .engine import build_dimension

    ranks = {}
    for d in discounts:
        res = build_dimension(
            scoring_views(reg, ft_discount=d), scoring_views(po, ft_discount=d),
            name="scoring", key="scoring",
            agg=SCORING_AGG, views=SCORING_VIEWS, playoff_mode="weighted",
        )
        ranks[f"FT={d}"] = res.set_index("player")["scoring_rank"]
    out = pd.DataFrame(ranks)
    out["range"] = out.max(axis=1) - out.min(axis=1)
    return out.sort_values("FT=0.7")
