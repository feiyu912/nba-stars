"""排名引擎: 四个维度共用的计算骨架。

统一的算法 (原先在 4 个脚本里各抄一份):
  1. 每个视角 (A/C) 分别算 巅峰5年均值 和 生涯均值 → 0.6 巅峰 + 0.4 生涯
  2. 季后赛处理:
       weighted   —— 得分/组织用。 按加权场次把常规赛和季后赛结果混合
       experience —— 防守/篮板用。 SPG/BPG/OREB 没有季后赛数据, 只能乘经验加成
  3. 两个视角各自排名, 取中位数, 再排名 → 最终名次

名次并列 (原实现的 bug):
  中位数会出现 x.5 (如 7 和 8 的中位数是 7.5), 原来的 `.astype(int)` 直接截断,
  人为制造出"并列"并让名次跳号 —— 101 名球员只有 76~82 个不同名次。
  现在保留中位数原值再排名, 只有真正相等的分数才算并列。
"""
from __future__ import annotations

import pandas as pd

from . import config
from .era import playoff_experience_bonus, playoff_weight

AggSpec = dict[str, str]      # 列名 → "mean" / "sum"
ViewSpec = dict[str, str]     # 视角名 → 数值列名


def summarize(df: pd.DataFrame, prefix: str, agg: AggSpec, views: ViewSpec) -> pd.DataFrame:
    """生涯均值 + 巅峰 N 年均值"""
    base = df.groupby("player").agg(agg).round(3).reset_index()
    base.columns = ["player"] + [f"{prefix}_{c}" for c in agg]

    parts = [base]
    for view, col in views.items():
        # 防御: 缺失值填充可能让数值列退化成 object, nlargest 会直接报错
        values = pd.to_numeric(df[col], errors="coerce")
        career = values.groupby(df["player"]).mean().round(4).reset_index()
        career.columns = ["player", f"{prefix}_{view}_career"]
        peak = values.groupby(df["player"]).apply(
            lambda s: s.nlargest(config.PEAK_YEARS).mean()).round(4).reset_index()
        peak.columns = ["player", f"{prefix}_{view}_peak"]
        parts.append(career)
        parts.append(peak)

    out = parts[0]
    for p in parts[1:]:
        out = out.merge(p, on="player")
    return out


def final_rank(view_ranks: list[pd.Series]) -> pd.Series:
    """两视角名次取中位数后排名。并列只在分数真正相等时出现。

    返回可空整数: 两个视角都没有数据的球员 (如 1973-74 前球员的防守)
    名次为 NA, 而不是被硬塞一个名次。
    """
    median = pd.concat(view_ranks, axis=1).median(axis=1)
    return median.rank(method="min").astype("Int64")


def build_dimension(
    reg: pd.DataFrame,
    po: pd.DataFrame | None,
    *,
    name: str,
    key: str,
    agg: AggSpec,
    views: ViewSpec,
    playoff_mode: str,
) -> pd.DataFrame:
    """跑完一个维度, 返回带 {key}_rank 的球员表。"""
    reg_sum = summarize(reg, "reg", agg, views)
    career = reg_sum

    if playoff_mode == "weighted":
        assert po is not None, f"{name}: weighted 模式需要季后赛数据"
        po_sum = summarize(po, "po", agg, views)
        career = reg_sum.merge(po_sum, on="player", how="left")
        for col in career.columns:
            if col.startswith("po_"):
                career[col] = career[col].fillna(0)
        career = pd.concat(
            [career, playoff_weight(career["reg_GP"], career["po_GP"])], axis=1
        )
        for view in views:
            career[f"reg_{view}"] = (config.PEAK_WEIGHT * career[f"reg_{view}_peak"]
                                     + (1 - config.PEAK_WEIGHT) * career[f"reg_{view}_career"])
            career[f"po_{view}"] = (config.PEAK_WEIGHT * career[f"po_{view}_peak"]
                                    + (1 - config.PEAK_WEIGHT) * career[f"po_{view}_career"])
            career[f"total_{view}"] = (career["reg_weight"] * career[f"reg_{view}"]
                                       + career["po_weight"] * career[f"po_{view}"])

    elif playoff_mode == "experience":
        assert po is not None, f"{name}: experience 模式需要季后赛数据来取场次"
        po_gp = po.groupby("player")["GP"].sum().reset_index()
        po_gp.columns = ["player", "po_GP"]
        career = reg_sum.merge(po_gp, on="player", how="left")
        career["po_GP"] = career["po_GP"].fillna(0)
        bonus = playoff_experience_bonus(career["po_GP"])
        for view in views:
            peak_career = (config.PEAK_WEIGHT * career[f"reg_{view}_peak"]
                           + (1 - config.PEAK_WEIGHT) * career[f"reg_{view}_career"])
            career[f"total_{view}"] = peak_career * bonus
    else:
        raise ValueError(f"未知的 playoff_mode: {playoff_mode}")

    view_ranks = []
    for view in views:
        r = career[f"total_{view}"].rank(ascending=False, method="min")
        career[f"total_{view}_rank"] = r.astype("Int64")
        view_ranks.append(r)

    career[f"{key}_median"] = pd.concat(view_ranks, axis=1).median(axis=1)
    career[f"{key}_rank"] = final_rank(view_ranks)
    rank = career[f"{key}_rank"]
    career[f"{key}_tied"] = rank.notna() & rank.duplicated(keep=False)
    return career.sort_values(f"{key}_rank", na_position="last").reset_index(drop=True)


def rank_quality_report(career: pd.DataFrame, key: str) -> str:
    """名次完整性: 唯一名次数、并列人数、无数据人数"""
    r = career[f"{key}_rank"]
    ranked = r.dropna()
    n_na = int(r.isna().sum())
    uniq = ranked.nunique()
    ties = int(career[f"{key}_tied"].sum())
    tail = f", 无数据 {n_na} 人" if n_na else ""
    return (f"{key:10s} 已排名 {len(ranked):3d} 人 (名次 1..{int(ranked.max()):3d}), "
            f"唯一值 {uniq:3d}, 并列 {ties:2d}{tail}")
