"""按正确顺序跑完所有维度并写出结果文件。

原实现的问题: 06/07/08/09 都隐式依赖 05 先跑过 (它们要读 results/scoring_ranking.csv),
顺序只存在于作者脑子里, 换个目录或新机器就会失败。

用法:
  python -m nbastars.run                 # 全部维度
  python -m nbastars.run --only scoring  # 单个维度
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import config, data, dimensions, engine
from .era import add_era_columns, add_era_z, career_era_group
from .ridge import fit_predict


def _write(df: pd.DataFrame, name: str) -> None:
    config.RESULTS_DIR.mkdir(exist_ok=True)
    path = config.RESULTS_DIR / name
    df.to_csv(path, index=False)
    print(f"    -> {path.relative_to(config.ROOT)}  ({len(df)} 行)")


def _playoff_gp(po: pd.DataFrame) -> pd.DataFrame:
    g = po.groupby("player")["GP"].sum().reset_index()
    g.columns = ["player", "po_GP"]
    return g


def run_scoring(reg: pd.DataFrame, po: pd.DataFrame) -> pd.DataFrame:
    print("[得分能力] 双视角 = 场均(罚球折算) x TS+ x 稀缺性 | 每分钟 x 竞争强度")
    res = engine.build_dimension(
        dimensions.scoring_views(reg), dimensions.scoring_views(po),
        name="scoring", key="scoring",
        agg=dimensions.SCORING_AGG, views=dimensions.SCORING_VIEWS,
        playoff_mode="weighted",
    )
    print(f"    {engine.rank_quality_report(res, 'scoring')}")
    res["FT_pct_scoring"] = (res["reg_FTM"] / res["reg_PPG"] * 100).round(1)
    _write(res[["player", "scoring_rank", "scoring_tied", "reg_PPG", "po_PPG",
                "reg_TS_pct", "po_TS_pct", "reg_GP", "po_GP", "FT_pct_scoring",
                "total_A_rank", "total_C_rank", "scoring_median"]],
           "scoring_ranking.csv")
    return res


def run_impact(reg: pd.DataFrame, db: pd.DataFrame) -> pd.DataFrame:
    print("[进攻影响力] 岭回归预测 O-DPM (代理目标), 特征为时代 Z-score")
    r = add_era_z(add_era_columns(reg), ["PPG", "TS_pct", "APG"])
    feats = r.groupby("player").agg({
        "PPG_era_z": "mean", "APG_era_z": "mean", "TS_pct_era_z": "mean"}).round(4).reset_index()
    peak = r.groupby("player")["PPG_era_z"].apply(
        lambda s: s.nlargest(config.PEAK_YEARS).mean()).round(4).reset_index()
    peak.columns = ["player", "peak_PPG_z"]

    target = db.groupby("player_name").agg({"o_dpm": "mean"}).round(3).reset_index()
    target.columns = ["player", "o_dpm"]

    base = feats.merge(peak, on="player").merge(target, on="player", how="left")
    features = ["PPG_era_z", "TS_pct_era_z", "APG_era_z", "peak_PPG_z"]
    result = fit_predict(base, features, "o_dpm")
    print(f"    {result.summary('ridge')}")
    print(f"    系数: {result.coefficients}")

    base["impact_score"] = result.predictions.values
    base["impact_rank"] = base["impact_score"].rank(ascending=False, method="min").astype(int)
    base = base.merge(add_era_columns(reg).groupby("player").agg(
        {"PPG": "mean", "APG": "mean", "TS_pct": "mean"}).round(3).reset_index()
        .rename(columns={"PPG": "reg_PPG", "APG": "reg_APG", "TS_pct": "reg_TS"}),
        on="player", how="left")
    base = base.sort_values("impact_rank").reset_index(drop=True)
    _write(base[["player", "impact_rank", "impact_score", "o_dpm",
                 "reg_PPG", "reg_APG", "reg_TS"]], "impact_ranking.csv")
    return base


def run_playmaking(reg: pd.DataFrame, po: pd.DataFrame) -> pd.DataFrame:
    print("[组织能力] 助攻 x 稀缺性 (助失比不进入指数, 仅作独立指标展示)")
    res = engine.build_dimension(
        dimensions.playmaking_views(reg), dimensions.playmaking_views(po),
        name="playmaking", key="play",
        agg=dimensions.PLAYMAKING_AGG, views=dimensions.PLAYMAKING_VIEWS,
        playoff_mode="weighted",
    )
    print(f"    {engine.rank_quality_report(res, 'play')}")
    covered = res["reg_ast_tov_recorded"].fillna(0)
    print(f"    有失误记录的赛季占比: {covered.mean() * 100:.0f}% — "
          f"助失比只对这些球员有效 (1977-78 起才记录), 但不影响名次")
    res["ast_tov_coverage"] = covered
    _write(res[["player", "play_rank", "play_tied", "reg_APG", "po_APG", "po_GP",
                "reg_ast_tov", "ast_tov_coverage",
                "total_A_rank", "total_C_rank"]], "playmaking_ranking.csv")
    return res


def run_defense(reg: pd.DataFrame, po: pd.DataFrame, db: pd.DataFrame) -> pd.DataFrame:
    print("[防守能力] STL+BLK x 稀缺性 | 1973-74 前无抢断/盖帽记录: 不填充, 显示 N/A")
    # 有效赛季数: 巅峰窗口是 5 年, 不足 5 个赛季的样本算不出可信的巅峰值
    seasons_with_data = reg.groupby("player")["SPG"].apply(lambda s: int(s.notna().sum()))
    eligible = seasons_with_data >= config.MIN_SEASONS_FOR_RANK

    res = engine.build_dimension(
        dimensions.defense_views(reg), po,
        name="defense", key="def",
        agg=dimensions.DEFENSE_AGG, views=dimensions.DEFENSE_VIEWS,
        playoff_mode="experience",
        eligible=eligible,
    )
    print(f"    {engine.rank_quality_report(res, 'def')}")

    res["seasons_with_def_data"] = res["player"].map(seasons_with_data).fillna(0).astype(int)
    res["defense_stats_missing"] = res["seasons_with_def_data"] == 0
    res["sample_too_small"] = res["seasons_with_def_data"].between(1, config.MIN_SEASONS_FOR_RANK - 1)
    n_missing = int(res["defense_stats_missing"].sum())
    n_thin = int(res["sample_too_small"].sum())
    print(f"    没有抢断/盖帽记录 (1973-74 之前): {n_missing} 人 — 不参与排名")
    print(f"    有效赛季不足 {config.MIN_SEASONS_FOR_RANK} 个 (算不出可信巅峰值): {n_thin} 人 — 不参与排名: "
          f"{', '.join(f'{r.player}({r.seasons_with_def_data}季)' for r in res[res['sample_too_small']].itertuples())}")

    r = add_era_z(add_era_columns(reg), ["SPG", "BPG"])
    feats = r.groupby("player").agg({"SPG_era_z": "mean", "BPG_era_z": "mean",
                                    "RPG": "mean"}).round(4).reset_index()
    peak = r.groupby("player")["SPG_era_z"].apply(
        lambda s: s.nlargest(config.PEAK_YEARS).mean()).round(4).reset_index()
    peak.columns = ["player", "peak_SPG_z"]
    target = db.groupby("player_name").agg({"d_dpm": "mean"}).round(3).reset_index()
    target.columns = ["player", "d_dpm"]
    base = feats.merge(peak, on="player").merge(target, on="player", how="left")
    features = ["SPG_era_z", "BPG_era_z", "RPG", "peak_SPG_z"]
    ridge = fit_predict(base, features, "d_dpm")
    print(f"    {ridge.summary('ridge')}")

    res = res.merge(base[["player", "d_dpm"]], on="player", how="left")
    res = res.merge(pd.DataFrame({"player": base["player"], "def_impact_score": ridge.predictions.values}),
                    on="player", how="left")
    # 没有数据或样本不足的人不做预测: 特征靠中位数填充、样本又薄, 预测值没有意义
    res.loc[res["defense_stats_missing"] | res["sample_too_small"], "def_impact_score"] = pd.NA
    res["def_impact_rank"] = res["def_impact_score"].rank(ascending=False, method="min").astype("Int64")

    res = res.rename(columns={"reg_def_output": "reg_def"})   # 展示用名 (与仪表盘一致)

    # 抢断榜 / 盖帽榜: 两种技能分开, 沿用同一套算法与最小样本规则
    for prefix, view_fn, agg, views in [
        ("stl", dimensions.steals_views, dimensions.STEALS_AGG, dimensions.STEALS_VIEWS),
        ("blk", dimensions.blocks_views, dimensions.BLOCKS_AGG, dimensions.BLOCKS_VIEWS),
    ]:
        sub = engine.build_dimension(
            view_fn(reg), po, name=prefix, key=prefix, agg=agg, views=views,
            playoff_mode="experience", eligible=eligible,
        )
        res = res.merge(sub[["player", f"{prefix}_rank"]], on="player", how="left")
    print(f"    抢断榜 {int(res['stl_rank'].notna().sum())} 人 | 盖帽榜 {int(res['blk_rank'].notna().sum())} 人")

    _write(res[["player", "def_rank", "def_tied", "reg_SPG", "reg_BPG", "reg_def",
                "stl_rank", "blk_rank",
                "po_GP", "defense_stats_missing", "sample_too_small", "seasons_with_def_data",
                "total_A_rank", "total_C_rank",
                "def_impact_rank", "def_impact_score", "d_dpm"]], "defense_ranking.csv")
    return res


def run_rebounding(reb: pd.DataFrame, po: pd.DataFrame) -> pd.DataFrame:
    print("[篮板能力] 总篮板 x 稀缺性 | 1973-74 前无 OREB/DREB 拆分: 不估算, 专项榜显示 N/A")
    views = dimensions.rebounding_views(reb)
    res = engine.build_dimension(
        views, po,
        name="rebounding", key="reb",
        agg=dimensions.REBOUNDING_AGG, views=dimensions.REBOUNDING_VIEWS,
        playoff_mode="experience",
    )
    print(f"    {engine.rank_quality_report(res, 'reb')}")
    split = reb.groupby("player")["OREB"]
    res["rebound_split_missing"] = res["player"].map(
        split.apply(lambda s: s.isna().all())).fillna(False)
    n_split = int(res["rebound_split_missing"].sum())
    print(f"    没有进攻/防守篮板拆分 (1973-74 之前): {n_split} 人 — "
          f"总篮板照常排名, OREB/DREB 专项榜显示 N/A")

    res = res.rename(columns={"reg_REB": "RPG", "reg_OREB": "OREB", "reg_DREB": "DREB"})
    for col in ["OREB", "DREB"]:
        peak = views.groupby("player")[col].apply(
            lambda s: s.nlargest(config.PEAK_YEARS).mean()).round(2).reset_index()
        peak.columns = ["player", f"peak_{col}"]
        res = res.merge(peak, on="player")
    # 用可空整数: 缺拆分的球员没有专项名次, 而不是被排到最后一名
    res["oreb_rank"] = res["peak_OREB"].rank(ascending=False, method="min").astype("Int64")
    res["dreb_rank"] = res["peak_DREB"].rank(ascending=False, method="min").astype("Int64")
    _write(res[["player", "reb_rank", "reb_tied", "RPG", "OREB", "DREB",
                "oreb_rank", "dreb_rank", "peak_OREB", "peak_DREB",
                "po_GP", "rebound_split_missing",
                "total_A_rank", "total_C_rank"]], "rebounding_ranking.csv")
    return res


def run_all(only: set[str] | None = None) -> dict[str, pd.DataFrame]:
    frames = data.load_all()
    print("=" * 72)
    print("数据")
    print("=" * 72)
    print(data.coverage_report(frames))

    reg, po, reb, db = frames["reg"], frames["po"], frames["reb"], frames["db"]
    def want(k: str) -> bool:
        return only is None or k in only
    out: dict[str, pd.DataFrame] = {}

    print()
    print("=" * 72)
    print("维度排名")
    print("=" * 72)
    scoring = run_scoring(reg, po) if want("scoring") else None
    impact = run_impact(reg, db) if want("impact") else None
    play = run_playmaking(reg, po) if want("playmaking") else None
    defense = run_defense(reg, po, db) if want("defense") else None
    rebounding = run_rebounding(reb, po) if want("rebounding") else None

    if scoring is not None:
        out["scoring"] = scoring
    if impact is not None:
        out["impact"] = impact
    if play is not None:
        out["playmaking"] = play
    if defense is not None:
        out["defense"] = defense
    if rebounding is not None:
        out["rebounding"] = rebounding

    # 汇总表: 一次读全, 避免 app.py 反复 merge 五份文件
    parts = []
    for _key, df, col in [("scoring", scoring, "scoring_rank"), ("impact", impact, "impact_rank"),
                         ("playmaking", play, "play_rank"), ("defense", defense, "def_rank"),
                         ("rebounding", rebounding, "reb_rank")]:
        if df is None:
            continue
        cols = ["player", col] + (["scoring_tied"] if col == "scoring_rank" else [])
        parts.append(df[cols])
    if len(parts) == 5:
        merged = parts[0]
        for p in parts[1:]:
            merged = merged.merge(p, on="player", how="outer")
        merged["era_group"] = merged["player"].map(
            reg.groupby("player")["season"].apply(career_era_group))
        merged["has_advanced_data"] = merged["player"].isin(set(db["player_name"]))
        _write(merged.sort_values("scoring_rank"), "all_rankings.csv")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="跑完所有维度并写出结果")
    ap.add_argument("--only", default=None,
                    help="只跑指定维度, 逗号分隔: scoring,impact,playmaking,defense,rebounding")
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    run_all(only)
    print("\n完成。查看仪表盘: streamlit run app.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
