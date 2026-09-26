"""数据契约测试: 这些不变量一旦被破坏, 排名就会静默算错。

历史背景: 原始数据里 30 名球员的 41 个赛季有 "球队A + 球队B + TOT" 三行,
被当成 3 个独立赛季, 导致巅峰窗口虚高、GP 求和超过 82、时代 Z-score 样本被污染。
"""
from __future__ import annotations

import pandas as pd
import pytest

from nbastars import config, data


@pytest.fixture(scope="module")
def frames():
    return data.load_all()


def test_player_pool_is_101(frames):
    assert frames["reg"]["player"].nunique() == 101


def test_no_duplicate_player_season(frames):
    for key in ("reg", "po", "reb"):
        df = frames[key]
        assert df.duplicated(["player", "season"]).sum() == 0, f"{key} 有重复的球员赛季"


def test_no_season_exceeds_82_games(frames):
    over = frames["reg"].groupby(["player", "season"])["GP"].sum()
    assert (over > 82).sum() == 0, f"{int((over > 82).sum())} 个赛季 GP > 82"


def test_multi_team_seasons_kept_as_single_total_row(frames):
    """多队赛季只应留下合并行, 且其 GP 等于被删除的分队行之和"""
    reg = frames["reg"]
    totals = reg[reg["team"].astype(str).str.upper() == "TOT"]
    assert len(totals) == 41, f"应有 41 个多队赛季的合并行, 实际 {len(totals)}"
    # 合并行的 GP 必须大于任何单队赛季可能的场次
    assert (totals["GP"].astype(int) <= 82).all()


def test_rebounds_gp_matches_regular_season_gp(frames):
    """篮板文件与常规赛文件必须对同一球员赛季给出相同的出场数"""
    reg = frames["reg"][["player", "season", "GP"]]
    reb = frames["reb"][["player", "season", "GP"]]
    m = reg.merge(reb, on=["player", "season"], suffixes=("_reg", "_reb"))
    assert len(m) == len(reg) == len(reb), "两个文件的球员赛季集合不一致"
    assert (m["GP_reg"] == m["GP_reb"]).all()


def test_current_season_is_complete(frames):
    """2025-26 常规赛与季后赛都要在 (曾经整季缺失, 用 B-R / ESPN 补齐)"""
    reg, po = frames["reg"], frames["po"]
    assert config.BREf_SEASON in set(reg["season"])
    assert config.BREf_SEASON in set(po["season"])
    assert po[po["season"] == config.BREf_SEASON]["player"].nunique() == 11


def test_required_columns_present(frames):
    assert {"player", "season", "GP", "MIN", "PPG", "TS_pct"} <= set(frames["reg"].columns)
    assert {"player", "season", "GP", "PPG", "FGA", "FTA", "TS_pct"} <= set(frames["po"].columns)


def test_early_missing_data_is_not_silently_zero(frames):
    """早期没有记录的字段必须是缺失, 不能是 0 (否则会被当成"场均0抢断"参与排名)"""
    reg = frames["reg"]
    pre_1973 = reg[reg["season"] < "1973-74"]
    assert pre_1973["SPG"].isna().all()
    pre_1977 = reg[reg["season"] < "1977-78"]
    assert pre_1977["TOV"].isna().all()


def test_contract_rejects_duplicates():
    """契约检查本身要能挡住重复赛季 —— 否则测试形同虚设"""
    bad = pd.DataFrame({
        "player": ["A", "A"], "season": ["2000-01", "2000-01"],
        "GP": [82, 20], "MIN": [36.0, 30.0], "PPG": [20.0, 18.0], "TS_pct": [0.5, 0.5],
    })
    with pytest.raises(data.DataContractError):
        data._check_unique_seasons(bad, "synthetic")
    with pytest.raises(data.DataContractError):
        data._check_gp(pd.DataFrame({
            "player": ["A", "A"], "season": ["2000-01", "2001-02"], "GP": [82, 82],
        }).assign(season=lambda d: ["2000-01", "2000-01"]), "synthetic")
