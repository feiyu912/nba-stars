"""时代修正: 把不同年代的原始数据折算到可比口径。

四个维度原先各写一份, 这里集中实现:
  pace 修正    每 48 分钟回合数折算到 PACE_TARGET (1960s 回合多, 数据要打折)
  竞争强度     sqrt(球队数 / 30) —— 8 支球队时代的联盟深度只有现代的 0.52 倍
  稀缺性       同年同池 Z-score → 1 + z*K, 低得分年代拿高分加成更多
  时代 Z-score 岭回归特征用, 让"1960 年代的 10 次助攻"和"2020 年代的 10 次助攻"区分开

注意: Z-score 的对比基准是"本项目 101 人池"而非全联盟 —— 池子偏向历史级球星,
所以 Z 会被压缩。要改成全联盟口径需要用联盟级数据重算 (见 README 已知局限)。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def add_era_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把 year / pace / lts / teams / competition / TS_plus 挂上去"""
    df = df.copy()
    df["year"] = df["season"].str[:4].astype(int)
    params = df["year"].map(config.era_params)
    df["pace"] = [p[0] for p in params]
    df["lts"] = [p[1] for p in params]
    df["teams"] = [p[2] for p in params]
    df["competition"] = (df["teams"] / config.COMPETITION_BASE).pow(0.5)
    df["pace_adj"] = config.PACE_TARGET / df["pace"]
    if "TS_pct" in df.columns:
        df["TS_plus"] = df["TS_pct"] / df["lts"]
    return df


def zscore_by_year(df: pd.DataFrame, col: str) -> pd.Series:
    """同年 Z-score。同期只有 1 人 (std 无效) 视为中性 0, 原始缺失保持缺失。"""
    g = df.groupby("year")[col]
    std = g.transform("std")
    z = (df[col] - g.transform("mean")) / std
    z = z.where(std.notna() & (std != 0), 0.0)
    return z.mask(df[col].isna())


def add_scarcity(df: pd.DataFrame, col: str, k: float = config.SCARCITY_K) -> pd.DataFrame:
    """稀缺性乘数: 同年 Z-score 越高, 说明该表现在这个年代越难得"""
    df = df.copy()
    df[f"{col}_z"] = zscore_by_year(df, col)
    df["scarcity"] = 1 + df[f"{col}_z"] * k
    return df


def add_era_z(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """岭回归特征用的时代 Z-score"""
    df = df.copy()
    for col in cols:
        df[f"{col}_era_z"] = zscore_by_year(df, col)
    return df


def per_minute(df: pd.DataFrame, col: str, minutes: str = "MIN") -> pd.Series:
    """每分钟产出。MIN 缺失时返回 NaN (不静默当 0 处理)"""
    return df[col] / df[minutes]


def career_era_group(seasons: pd.Series) -> str:
    """按生涯中位赛季判断所处年代。

    原实现用"是否有 databallr 数据"来判断, 结果把 Michael Jordan 标成了
    "Modern (2001+)" —— 那是数据可得性, 不是年代。
    """
    years = seasons.astype(str).str[:4].astype(int)
    return "Modern (2000+)" if years.median() >= 2000 else "Historical (pre-2000)"


def playoff_weight(reg_gp: pd.Series, po_gp: pd.Series,
                   multiplier: int = config.PLAYOFF_MULTIPLIER) -> pd.DataFrame:
    """按加权场次算常规赛/季后赛权重。

    每场季后赛 = multiplier 场常规赛。没打过季后赛的球员权重全给常规赛,
    因此不会因为"季后赛样本小"而占便宜或吃亏。
    """
    weighted = po_gp * multiplier
    total = reg_gp + weighted
    po_w = np.where(total > 0, weighted / total.replace(0, np.nan), 0.0)
    po_w = np.nan_to_num(po_w, nan=0.0)
    return pd.DataFrame({"po_weight": po_w, "reg_weight": 1 - po_w})


def playoff_experience_bonus(po_gp: pd.Series,
                             k: float = config.PLAYOFF_EXPERIENCE_K) -> pd.Series:
    """季后赛经验加成: 打得越多说明越经得起检验。

    防守/篮板用这个而不是季后赛加权 —— 因为 SPG/BPG/OREB 没有季后赛数据,
    只能用常规赛值乘一个经验系数。这是权宜之计, 不是等价替代。
    """
    return 1 + np.log1p(po_gp / 82) * k
