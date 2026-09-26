"""防守能力排名 (计算逻辑在 nbastars 包内)

用法: python notebooks/09_defense.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from nbastars import data, run  # noqa: E402


def main() -> int:
    frames = data.load_all()
    res = run.run_defense(frames["reg"], frames["po"], frames["db"])

    print()
    print("=" * 92)
    print("防守产出 TOP 30")
    print("=" * 92)
    print(f"{'Rk':>3s}  {'Player':26s} {'SPG':>5s} {'BPG':>5s} {'S+B':>5s} {'poGP':>5s}  备注")
    print("-" * 80)
    for _, r in res.head(30).iterrows():
        note = "无抢断/盖帽数据(1973-74 前, 不参与排名)" if r["defense_stats_missing"] else ""
        rank = f"{int(r['def_rank']):3d}" if pd.notna(r["def_rank"]) else "  -"
        print(f" {rank}  {r['player']:26s} {r['reg_SPG']:5.1f} "
              f"{r['reg_BPG']:5.1f} {r['reg_def']:5.1f} {int(r['po_GP']):5d}  {note}")

    print()
    print("=" * 92)
    print("防守影响力 (岭回归预测 D-DPM) TOP 20")
    print("=" * 92)
    print(f"\n{'Rk':>3s}  {'Player':26s} {'Pred':>6s} {'Actual':>7s}  {'SPG':>4s} {'BPG':>4s}")
    print("-" * 62)
    impact = res.sort_values("def_impact_rank")
    for _, r in impact.head(20).iterrows():
        actual = f"{r['d_dpm']:+5.2f}*" if r["d_dpm"] == r["d_dpm"] else "    - "
        print(f" {int(r['def_impact_rank']):3d}  {r['player']:26s} "
              f"{r['def_impact_score']:+5.2f}  {actual}  {r['reg_SPG']:4.1f} {r['reg_BPG']:4.1f}")

    print()
    print("=" * 92)
    print("交叉对比: 得分 vs 防守")
    print("=" * 92)
    scoring = data.load_regular().groupby("player").agg({"PPG": "mean"}).round(1).reset_index()
    cross = res[["player", "def_rank"]].merge(scoring, on="player")
    cross = cross.sort_values("def_rank").head(25)
    for _, r in cross.iterrows():
        print(f"  {r['player']:26s} 防守 #{int(r['def_rank']):3d}   生涯 {r['PPG']:5.1f} PPG")
    return 0


if __name__ == "__main__":
    sys.exit(main())
