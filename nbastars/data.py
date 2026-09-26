"""数据加载与契约校验。

关键约定 (脚本会强制检查, 违反直接报错而不是静默算错):
  1. (player, season) 唯一 —— 多队赛季只保留合并行 (TOT)。
     原始数据里 30 名球员的 41 个赛季有 "球队A + 球队B + TOT" 三行,
     被当成 3 个独立赛季会让巅峰窗口、GP 求和、时代 Z-score 全部失真。
     历史上就踩过这个坑, 所以这里做成硬断言。
  2. 单个赛季 GP <= 82。
  3. 早期缺失的字段不静默填充, 由使用方显式决定 (见 config.EARLY_MISSING)。

路径基于包位置解析, 因此从任何工作目录运行都能找到数据 (原脚本用相对路径, 只能在仓库根目录跑)。
"""
from __future__ import annotations

import pandas as pd

from . import config

# 各数据源对球员名的写法不一致, 统一映射 (原代码在 4 个脚本里各写一份)
DATABALLR_NAME_MAP = {
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
}


class DataContractError(AssertionError):
    pass


def _read(name: str) -> pd.DataFrame:
    path = config.DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"缺少数据文件 {path}")
    return pd.read_csv(path)


def _check_unique_seasons(df: pd.DataFrame, label: str) -> None:
    dup = df.duplicated(["player", "season"]).sum()
    if dup:
        bad = df[df.duplicated(["player", "season"], keep=False)].sort_values(["player", "season"])
        sample = bad[["player", "season"]].drop_duplicates().head(5).to_dict("records")
        raise DataContractError(
            f"{label}: 有 {dup} 行重复的 (player, season)。"
            f"多队赛季必须只保留合并行 TOT。样例: {sample}"
        )


def _check_gp(df: pd.DataFrame, label: str) -> None:
    over = df.groupby(["player", "season"])["GP"].sum()
    over = over[over > 82]
    if len(over):
        raise DataContractError(
            f"{label}: {len(over)} 个赛季 GP 之和超过 82, 说明赛季被重复计算。样例: "
            f"{over.head(3).to_dict()}"
        )


def load_regular() -> pd.DataFrame:
    df = _read("nba100_career_all.csv")
    _check_unique_seasons(df, "nba100_career_all.csv")
    _check_gp(df, "nba100_career_all.csv")
    return df


def load_playoffs() -> pd.DataFrame:
    df = _read("nba100_playoffs.csv")
    _check_unique_seasons(df, "nba100_playoffs.csv")
    return df


def load_rebounds() -> pd.DataFrame:
    df = _read("nba100_rebounds.csv")
    _check_unique_seasons(df, "nba100_rebounds.csv")
    return df


def load_databallr() -> pd.DataFrame:
    df = _read("nba100_databallr.csv")
    df["player_name"] = df["player_name"].replace(DATABALLR_NAME_MAP)
    return df


def load_all() -> dict[str, pd.DataFrame]:
    return {
        "reg": load_regular(),
        "po": load_playoffs(),
        "reb": load_rebounds(),
        "db": load_databallr(),
    }


def coverage_report(frames: dict[str, pd.DataFrame]) -> str:
    """数据覆盖情况: 缺失集中在早期赛季, 打印出来避免被当成 0 参与计算"""
    reg, po = frames["reg"], frames["po"]
    lines = [
        f"常规赛 {len(reg)} 行 / {reg['player'].nunique()} 人 / {reg['season'].nunique()} 个赛季"
        f" ({reg['season'].min()} → {reg['season'].max()})",
        f"季后赛 {len(po)} 行 ({po['season'].min()} → {po['season'].max()})",
    ]
    for col, why in config.EARLY_MISSING.items():
        if col in reg.columns:
            n = int(reg[col].isna().sum())
            if n:
                lines.append(f"  缺失 {col}: {n} 行 — {why}")
    return "\n".join(lines)
