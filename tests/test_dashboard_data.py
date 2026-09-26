"""仪表盘数据装配测试。

盯住一类反复出现过的 bug: 合并两个都含同名列的表, pandas 会生成
`def_rank_x` / `def_rank_y`, 之后按 `def_rank` 取列就 KeyError。
(这个 bug 实际发生过: all_rankings.csv 和 defense_ranking.csv 都带 def_rank。)
"""
from __future__ import annotations

import pandas as pd
import pytest

from nbastars import config
from nbastars.dashboard_data import RANK_COLUMNS, build_career_frame, load_dimension


@pytest.fixture(scope="module")
def career() -> pd.DataFrame:
    return build_career_frame(config.DATA_DIR, config.RESULTS_DIR)


def test_no_merge_collision_suffixes(career):
    leftovers = [c for c in career.columns if c.endswith(("_x", "_y"))]
    assert not leftovers, f"合并产生了同名列残留: {leftovers}"


def test_all_players_present(career):
    assert len(career) == 101
    assert career["player"].is_unique


def test_required_columns_exist(career):
    needed = set(RANK_COLUMNS) | {
        "player", "PPG", "APG", "TS_pct", "GP", "purity", "ast_tov",
        "pct_2P", "pct_3P", "pct_FT", "po_PPG", "po_GP", "po_delta",
        "reb_RPG", "reb_OREB", "reb_DREB",
    }
    assert needed <= set(career.columns), f"缺少列: {sorted(needed - set(career.columns))}"


def test_ranks_come_from_all_rankings(career):
    """名次的唯一来源是 all_rankings.csv"""
    ranks = pd.read_csv(config.RESULTS_DIR / "all_rankings.csv")
    merged = career.set_index("player")["def_rank"]
    expected = ranks.set_index("player")["def_rank"]
    assert merged.reindex(expected.index).equals(expected)


def test_defense_exclusions_stay_missing(career):
    """防守被排除的球员在仪表盘数据里必须是空名次, 不能被填成 0"""
    missing = career[career["def_rank"].isna()]
    assert len(missing) == 19
    assert not (career["def_rank"] == 0).any()


def test_ast_tov_is_na_when_turnovers_missing(career):
    cousy = career[career["player"] == "Bob Cousy"].iloc[0]
    assert pd.isna(cousy["ast_tov"]), "1977-78 前没有失误记录, 助失比必须是空"
    stockton = career[career["player"] == "John Stockton"].iloc[0]
    assert stockton["ast_tov"] > 3


def test_scoring_share_columns_sum_to_100(career):
    total = career["pct_2P"] + career["pct_3P"] + career["pct_FT"]
    assert total.between(99.5, 100.5).all()


def test_defense_dimension_marks_excluded_players():
    d = load_dimension(config.RESULTS_DIR, "defense_ranking.csv")
    assert int(d["defense_stats_missing"].sum()) == 11
    assert int(d["sample_too_small"].sum()) == 8
    assert int(d["def_rank"].notna().sum()) == 82