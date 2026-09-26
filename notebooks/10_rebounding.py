"""篮板能力排名 (计算逻辑在 nbastars 包内)

用法: python notebooks/10_rebounding.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbastars import data, run  # noqa: E402


def main() -> int:
    frames = data.load_all()
    res = run.run_rebounding(frames["reb"], frames["po"])

    print()
    print("=" * 92)
    print("总篮板 TOP 30")
    print("=" * 92)
    print(f"{'Rk':>3s}  {'Player':26s} {'RPG':>5s} {'ORB':>5s} {'DRB':>5s} {'poGP':>5s}")
    print("-" * 72)
    for _, r in res.head(30).iterrows():
        print(f" {int(r['reb_rank']):3d}  {r['player']:26s} {r['RPG']:5.1f} "
              f"{r['OREB']:5.1f} {r['DREB']:5.1f} {int(r['po_GP']):5d}")

    for label, col in [("进攻篮板 TOP 15 (创造二次进攻)", "oreb_rank"),
                       ("防守篮板 TOP 15 (终结回合)", "dreb_rank")]:
        print()
        print("=" * 92)
        print(label)
        print("=" * 92)
        peak_col = "peak_OREB" if col == "oreb_rank" else "peak_DREB"
        for _, r in res.sort_values(col).head(15).iterrows():
            print(f"  #{int(r[col]):3d}  {r['player']:26s}  巅峰5年 {r[peak_col]:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
