"""指标构造测试: 时代修正、稀缺性、缺失值标记"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nbastars import dimensions
from nbastars.era import add_era_columns, career_era_group, per_minute, zscore_by_year


def _season_row(**kw) -> pd.DataFrame:
    base = {
        "player": ["A"], "season": ["2000-01"], "team": ["LAL"], "GP": [82],
        "MIN": [36.0], "PPG": [20.0], "FGM": [7.0], "FGA": [15.0], "FTM": [4.0],
        "FTA": [5.0], "FT_PCT": [0.8], "TS_pct": [0.55], "APG": [5.0], "RPG": [6.0],
        "SPG": [1.5], "BPG": [0.8], "TOV": [3.0], "FG3M": [1.0],
    }
    base.update(kw)
    return pd.DataFrame(base)


def test_era_columns_use_period_table():
    df = add_era_columns(_season_row(season=["1990-91"]))
    assert df["pace"].iloc[0] == 95
    assert df["teams"].iloc[0] == 26
    assert df["competition"].iloc[0] == (26 / 30) ** 0.5
    assert df["pace_adj"].iloc[0] == 97 / 95


def test_era_fallback_for_unknown_year():
    df = add_era_columns(_season_row(season=["1940-41"]))
    assert df["pace"].iloc[0] == 97


def test_zscore_is_neutral_when_cohort_has_one_player():
    """同期只有 1 人时 std 无效 —— 应视为中性 0, 而不是让整个赛季变成 NaN 被丢弃"""
    df = pd.DataFrame({"year": [1960], "PPG": [30.0]})
    z = zscore_by_year(df, "PPG")
    assert z.iloc[0] == 0.0


def test_zscore_preserves_missing_values():
    df = pd.DataFrame({"year": [2000, 2000, 2000], "SPG": [1.0, np.nan, 2.0]})
    z = zscore_by_year(df, "SPG")
    assert pd.isna(z.iloc[1])


def test_zscore_is_zero_mean_within_year():
    df = pd.DataFrame({"year": [2000] * 4 + [2001] * 4,
                       "PPG": [10, 20, 30, 40, 1, 2, 3, 100]})
    z = zscore_by_year(df, "PPG")
    assert z.groupby(df["year"]).mean().abs().max() < 1e-12


def test_scarcity_centers_on_one():
    df = pd.DataFrame({"year": [2000] * 3, "PPG": [10.0, 20.0, 30.0]})
    out = dimensions.add_scarcity(df, "PPG") if hasattr(dimensions, "add_scarcity") else None
    from nbastars.era import add_scarcity
    out = add_scarcity(df, "PPG")
    assert out["scarcity"].mean().round(6) == 1.0
    assert out["scarcity"].iloc[2] > 1.0


def test_per_minute_returns_nan_when_minutes_missing():
    df = _season_row(MIN=[np.nan])
    assert pd.isna(per_minute(df, "PPG").iloc[0])


def test_defense_does_not_impute_missing_stats():
    """1973-74 之前没有抢断/盖帽 —— 必须保持缺失, 不许填充。

    填充会造出一个假名次 (曾经用中位数填过, 导致 11 名早期球员拿到凭空的防守排名)。
    """
    df = pd.concat([
        _season_row(season=["1970-71"], SPG=[np.nan], BPG=[np.nan]),
        _season_row(season=["1980-81"], player=["B"]),
    ], ignore_index=True)
    out = dimensions.defense_views(df)
    pre = out[out["player"] == "A"]
    assert pre["SPG"].isna().all() and pre["BPG"].isna().all()
    assert pre["def_output"].isna().all(), "缺失的防守数据不能变成任何数值"
    assert pre["defA"].isna().all(), "没有数据就不应该有得分"
    # 有数据的球员不受影响
    post = out[out["player"] == "B"]
    assert post["def_output"].iloc[0] == pytest.approx(1.5 + 0.8)


def test_playmaking_does_not_use_turnovers_in_the_index():
    """助失比必须留在指数之外 —— 1977-78 前没有失误记录, 用它做乘数会让两个时代不可比。

    这条曾经真实发生过: 用联盟平均失误数填空并当乘数, Oscar Robertson 靠这个
    编造的数字排到组织榜 #6。
    """
    with_tov = dimensions.playmaking_views(_season_row(TOV=[3.0]))
    without_tov = dimensions.playmaking_views(_season_row().drop(columns=["TOV"]))

    # 指数只由 APG / 节奏 / 竞争强度 / 稀缺度决定: 失误不同, 指数必须完全相同
    assert with_tov["playA"].iloc[0] == pytest.approx(without_tov["playA"].iloc[0])
    assert with_tov["playC"].iloc[0] == pytest.approx(without_tov["playC"].iloc[0])

    # 助失比仍然算, 但缺记录时是缺失 (不填充), 并打上"无记录"标记
    assert with_tov["ast_tov"].iloc[0] == pytest.approx(5.0 / 3.0)
    assert bool(with_tov["ast_tov_recorded"].iloc[0]) is True
    assert pd.isna(without_tov["ast_tov"].iloc[0])
    assert bool(without_tov["ast_tov_recorded"].iloc[0]) is False


def test_rebounding_does_not_estimate_oreb_dreb_split():
    """1973-74 之前没有进攻/防守篮板拆分 —— 不许按 30/70 估算"""
    df = _season_row(OREB=[np.nan], DREB=[np.nan], REB=[10.0])
    out = dimensions.rebounding_views(df)
    assert pd.isna(out["OREB"].iloc[0]) and pd.isna(out["DREB"].iloc[0])
    # 但总篮板两个视角必须照常算出来 (REB 从 1950-51 起就有)
    assert out["rebA"].notna().all()
    assert out["rebC"].notna().all()


def test_era_group_uses_median_season_not_data_availability():
    """原来的实现把 Jordan 标成了 'Modern (2001+)' —— 那是数据可得性, 不是年代"""
    jordan = pd.Series([f"{y}-{str(y + 1)[2:]}" for y in range(1984, 2003)])
    lebron = pd.Series([f"{y}-{str(y + 1)[2:]}" for y in range(2003, 2027)])
    assert career_era_group(jordan) == "Historical (pre-2000)"
    assert career_era_group(lebron) == "Modern (2000+)"
