"""排名引擎测试: 名次并列、季后赛权重、巅峰窗口"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nbastars import config, engine
from nbastars.era import playoff_experience_bonus, playoff_weight


def test_final_rank_does_not_truncate_half_ranks():
    """中位数 7.5 不能被截断成 7 —— 原实现在这里制造了假并列"""
    a = pd.Series([7, 8, 9], index=["x", "y", "z"])
    c = pd.Series([8, 7, 9], index=["x", "y", "z"])
    rank = engine.final_rank([a, c])
    assert rank["x"] == 1 and rank["y"] == 1   # 两人中位数都是 7.5, 真并列
    assert rank["z"] == 3                       # 名次跳到 3, 是竞赛排名语义
    assert rank["z"] == 3 and list(rank) == [1, 1, 3]


def test_final_rank_is_unique_for_distinct_scores():
    a = pd.Series([1, 5, 9, 13], index=list("wxyz"))
    c = pd.Series([2, 6, 10, 14], index=list("wxyz"))
    rank = engine.final_rank([a, c])
    assert rank.nunique() == 4
    assert rank.max() == 4


def test_playoff_weight_no_playoffs_gives_zero_weight():
    w = playoff_weight(pd.Series([1000]), pd.Series([0]))
    assert w["po_weight"].iloc[0] == 0.0
    assert w["reg_weight"].iloc[0] == 1.0


def test_playoff_weight_matches_multiplier():
    """每场季后赛按 multiplier 场常规赛折算"""
    w = playoff_weight(pd.Series([82]), pd.Series([20]))
    expected = 20 * config.PLAYOFF_MULTIPLIER / (82 + 20 * config.PLAYOFF_MULTIPLIER)
    assert w["po_weight"].iloc[0] == pytest.approx(expected)
    assert w["po_weight"].iloc[0] + w["reg_weight"].iloc[0] == pytest.approx(1.0)


def test_playoff_experience_bonus_is_bounded_and_monotonic():
    b = playoff_experience_bonus(pd.Series([0, 82, 164, 246]))
    assert b.iloc[0] == 1.0
    assert list(b) == sorted(b)
    assert b.max() < 1.5   # 温和加成, 不能盖过产出本身


def test_summarize_uses_top_n_peak():
    df = pd.DataFrame({
        "player": ["A"] * 8,
        "season": [f"199{i}-9{i}" for i in range(8)],
        "GP": [82] * 8,
        "value": [1.0, 2, 3, 4, 5, 6, 7, 100],
    })
    out = engine.summarize(df, "reg", {"GP": "sum"}, {"v": "value"})
    assert out["reg_v_career"].iloc[0] == pytest.approx(np.mean([1, 2, 3, 4, 5, 6, 7, 100]))
    top5 = np.mean([100, 7, 6, 5, 4])
    assert out["reg_v_peak"].iloc[0] == pytest.approx(top5)


def test_summarize_survives_object_dtype_values():
    """填充缺失值可能让数值列退化成 object, 引擎要能兜住"""
    df = pd.DataFrame({
        "player": ["A", "A", "A"],
        "season": ["2000-01", "2001-02", "2002-03"],
        "GP": [82, 82, 82],
        "value": pd.Series([1.0, None, 3.0], dtype=object),
    })
    out = engine.summarize(df, "reg", {"GP": "sum"}, {"v": "value"})
    # 不足 5 个赛季时 peak 就是现有赛季的均值 (与历史行为一致)
    assert out["reg_v_peak"].iloc[0] == pytest.approx(np.mean([1.0, 3.0]))
