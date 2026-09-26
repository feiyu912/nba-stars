"""组织能力排名 (计算逻辑在 nbastars 包内)

用法: python notebooks/08_playmaking.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbastars import data, run  # noqa: E402


def main() -> int:
    frames = data.load_all()
    res = run.run_playmaking(frames["reg"], frames["po"])
    scoring = data.load_regular()

    print()
    print("=" * 92)
    print("组织能力 TOP 30")
    print("=" * 92)
    print(f"{'Rk':>3s}  {'Player':26s} {'APG':>5s} {'TOV':>5s} {'A/T':>5s} "
          f"{'poAPG':>6s} {'poGP':>5s}  估算TOV")
    print("-" * 80)
    for _, r in res.head(30).iterrows():
        po_apg = f"{r['po_APG']:5.1f}" if r["po_GP"] > 0 else "  N/A"
        mark = " 是" if r["TOV_imputed_share"] > 0.5 else ""
        print(f" {int(r['play_rank']):3d}  {r['player']:26s} {r['reg_APG']:5.1f} "
              f"{r['reg_TOV']:5.1f} {r['reg_ast_tov']:5.2f} {po_apg} {int(r['po_GP']):5d}{mark}")

    print()
    print("=" * 92)
    print("交叉对比: 得分 vs 组织")
    print("=" * 92)
    reg_career = scoring.groupby("player").agg({"PPG": "mean"}).round(1).reset_index()
    cross = res[["player", "play_rank"]].merge(
        reg_career.rename(columns={"PPG": "career_PPG"}), on="player")

    def classify(r) -> str:
        if r["play_rank"] <= 15 and r["career_PPG"] >= 22:
            return "得分组织兼备"
        if r["play_rank"] <= 15:
            return "纯组织者"
        if r["play_rank"] > 30 and r["career_PPG"] >= 25:
            return "纯得分手"
        return ""

    cross["类型"] = cross.apply(classify, axis=1)
    cross = cross.sort_values("play_rank")
    for _, r in cross.head(25).iterrows():
        print(f"  {r['player']:26s} 组织 #{int(r['play_rank']):3d}  "
              f"生涯 {r['career_PPG']:5.1f} PPG   {r['类型']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
