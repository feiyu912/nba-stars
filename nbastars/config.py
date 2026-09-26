"""全局参数: 时代基准、权重、阈值、路径。

原先这些数字散落在 4 个脚本里各写一份 (时代参数表 4 份、季后赛权重 4 份),
改一处就会与其它维度不一致。集中在这里, 便于做敏感性分析。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

# ── 时代基准 (按赛季起始年归组) ──
# pace: 每 48 分钟回合数; lts: 联盟平均真实命中率; teams: 联盟球队数
ERA_TABLE: list[tuple[int, int, int, float, int]] = [
    (1955, 1965, 125, 0.460, 9),
    (1965, 1975, 110, 0.490, 15),
    (1975, 1985, 103, 0.520, 23),
    (1985, 1995, 95, 0.535, 26),
    (1995, 2005, 91, 0.530, 29),
    (2005, 2015, 95, 0.545, 30),
    (2015, 2026, 100, 0.570, 30),
]
ERA_FALLBACK = (97, 0.545, 30)

PACE_TARGET = 97              # pace 修正目标值
COMPETITION_BASE = 30         # 竞争强度基准球队数
PLAYOFF_MULTIPLIER = 3        # 每场季后赛 = 3 场常规赛
PEAK_YEARS = 5                # 巅峰窗口
PEAK_WEIGHT = 0.6             # 巅峰/生涯加权 (0.6 巅峰 + 0.4 生涯)
FT_DISCOUNT = 0.7             # 罚球折算系数 (敏感性分析: 0.6 / 0.7 / 0.8)
SCARCITY_K = 0.1              # 稀缺性斜率: 1 + z * K
RIDGE_ALPHA = 2.0
PLAYOFF_EXPERIENCE_K = 0.1    # 防守/篮板用的季后赛经验加成斜率
MIN_SEASONS_FOR_TREND = 3

# 2025-26 及之后: 常规赛数据来自 Basketball-Reference, 季后赛来自 ESPN (见 README)
BREf_SEASON = "2025-26"

EARLY_MISSING = {
    "MIN": "1951-52 赛季之前没有出场时间记录",
    "SPG": "1973-74 赛季之前没有抢断记录",
    "BPG": "1973-74 赛季之前没有盖帽记录",
    "TOV": "1977-78 赛季之前没有失误记录",
    "REB": "1950-51 赛季之前没有篮板记录",
    "FG3M": "1979-80 赛季之前没有三分线",
    "OREB": "1973-74 赛季之前没有进攻/防守篮板拆分",
}


def era_params(year: int) -> tuple[int, float, int]:
    """返回 (pace, 联盟平均TS%, 球队数)"""
    for lo, hi, pace, lts, teams in ERA_TABLE:
        if lo <= year < hi:
            return pace, lts, teams
    return ERA_FALLBACK
