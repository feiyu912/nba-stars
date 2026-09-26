"""得分能力 + 进攻影响力 (含敏感性分析与解释层)

计算逻辑在 nbastars 包里 (见 nbastars/dimensions.py, nbastars/engine.py)。
这个脚本只负责跑出来并打印分析报告。

用法: python notebooks/05_consensus_ranking.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbastars import config, data, dimensions, run  # noqa: E402
from nbastars.era import add_era_columns  # noqa: E402


def print_scoring_table(next_to: pd.DataFrame) -> None:
    print("=" * 100)
    print("表1: 得分能力排名")
    print("=" * 100)
    print("""
方法:
  A = PPG(罚球折算 0.7) x pace修正 x TS+ x 稀缺性
  C = 每分钟得分 x TS+ x 竞争强度 x 稀缺性
  每场季后赛 = 3 场常规赛, 按加权场次决定常规赛/季后赛权重
  最终名次 = A/C 两视角名次的中位数 (真并列才并列)
""")
    print(f"{'Rk':>3s}  {'Player':26s} {'A':>3s} {'C':>3s}  {'regPPG':>6s} {'poPPG':>6s} "
          f"{'poGP':>4s} {'FT%s':>5s}")
    print("-" * 78)
    for _, r in next_to.head(30).iterrows():
        po_ppg = f"{r['po_PPG']:5.1f}" if r["po_GP"] > 0 else "  N/A"
        tied = "*" if r.get("scoring_tied") else " "
        print(f" {int(r['scoring_rank']):3d}{tied} {r['player']:26s} "
              f"{int(r['total_A_rank']):3d} {int(r['total_C_rank']):3d}  "
              f"{r['reg_PPG']:5.1f}  {po_ppg} {int(r['po_GP']):4d} "
              f"{r['FT_pct_scoring']:4.1f}%")


def print_impact_table(impact: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("表2: 进攻影响力排名 (岭回归预测 O-DPM)")
    print("=" * 100)
    # impact 表里已经带了 reg_PPG / reg_APG, 不要再 merge 一次 (会造成列名冲突)
    print(f"\n{'Rk':>3s}  {'Player':26s} {'Pred':>6s} {'Actual':>7s}  {'PPG':>5s} {'APG':>4s}")
    print("-" * 62)
    for _, r in impact.head(30).iterrows():
        actual = f"{r['o_dpm']:+5.2f}*" if pd.notna(r["o_dpm"]) else "    - "
        print(f" {int(r['impact_rank']):3d}  {r['player']:26s} "
              f"{r['impact_score']:+5.2f}  {actual}  {r['reg_PPG']:5.1f} {r['reg_APG']:4.1f}")
    print("\n* = 有实际数据可训练 (53 人); 其余为模型外推")


def print_sensitivity(reg: pd.DataFrame, po: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("敏感性分析: 罚球折算系数 0.6 / 0.7 / 0.8")
    print("=" * 100)
    sens = dimensions.ft_discount_sensitivity(reg, po)
    print(f"\n{'Player':26s} {'FT=0.6':>7s} {'FT=0.7':>7s} {'FT=0.8':>7s} {'波动':>4s}  判定")
    print("-" * 66)
    for player, r in sens.head(25).iterrows():
        verdict = "稳定" if r["range"] <= 2 else ("轻微" if r["range"] <= 5 else "敏感")
        print(f"  {player:24s} #{int(r['FT=0.6']):4d}  #{int(r['FT=0.7']):4d}  "
              f"#{int(r['FT=0.8']):4d}  {int(r['range']):3d}   {verdict}")
    worst = sens.nlargest(5, "range")
    print("\n对罚球系数最敏感的球员:")
    for player, r in worst.iterrows():
        print(f"  {player:24s} 波动 {int(r['range'])} 位 — 罚球占得分比重高, 系数一变名次就动")


def print_explanation(reg: pd.DataFrame, next_to: pd.DataFrame) -> None:
    print()
    print("=" * 100)
    print("解释层: TOP 20 为什么排在这里")
    print("=" * 100)
    r = add_era_columns(reg)
    peaks = r.groupby("player")["PPG"].apply(
        lambda s: s.nlargest(config.PEAK_YEARS).mean()).round(2)

    for _, row in next_to.head(20).iterrows():
        player = row["player"]
        factors = []
        if row["reg_PPG"] > 25:
            factors.append(f"+ 高产得分手 (生涯 {row['reg_PPG']:.1f} PPG)")
        elif row["reg_PPG"] > 20:
            factors.append(f"+ 稳定得分手 (生涯 {row['reg_PPG']:.1f} PPG)")
        else:
            factors.append(f"- 得分产量偏低 ({row['reg_PPG']:.1f} PPG)")

        if row["reg_TS_pct"] > 0.58:
            factors.append(f"+ 效率顶级 (TS% {row['reg_TS_pct']:.3f})")
        elif row["reg_TS_pct"] < 0.52:
            factors.append(f"- 效率偏低 (TS% {row['reg_TS_pct']:.3f})")

        if row["FT_pct_scoring"] > 28:
            factors.append(f"- 罚球依赖高 ({row['FT_pct_scoring']:.1f}% 的得分来自罚球, 被折算)")
        elif row["FT_pct_scoring"] < 18:
            factors.append(f"+ 罚球依赖低 ({row['FT_pct_scoring']:.1f}%)")

        peak = peaks.get(player)
        if peak is not None and peak - row["reg_PPG"] > 3:
            factors.append(f"+ 巅峰明显高于生涯均值 (巅峰5年 {peak:.1f} vs 生涯 {row['reg_PPG']:.1f})")

        if row["po_GP"] > 100:
            delta = row["po_PPG"] - row["reg_PPG"]
            if delta > 0:
                factors.append(f"+ 季后赛更强 ({row['po_PPG']:.1f} vs {row['reg_PPG']:.1f}, "
                               f"{int(row['po_GP'])} 场)")
            else:
                factors.append(f"~ 季后赛略降 ({row['po_PPG']:.1f} vs {row['reg_PPG']:.1f})")
        elif row["po_GP"] > 0:
            factors.append(f"~ 季后赛样本有限 ({int(row['po_GP'])} 场)")
        else:
            factors.append("- 没有季后赛数据")

        print(f"\n#{int(row['scoring_rank']):3d} {player}")
        for f in factors:
            print(f"     {f}")


def main() -> int:
    frames = data.load_all()
    reg, po = frames["reg"], frames["po"]
    print(data.coverage_report(frames))
    print()

    scoring = run.run_scoring(reg, po)
    scoring["FT_pct_scoring"] = (scoring["reg_FTM"] / scoring["reg_PPG"] * 100).round(1)
    impact = run.run_impact(reg, frames["db"])

    print_scoring_table(scoring)
    print_impact_table(impact)
    print_sensitivity(reg, po)
    print_explanation(reg, scoring)

    print(f"\n结果目录: {config.RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
