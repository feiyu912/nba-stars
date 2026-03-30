"""
Rebounding Ranking: 篮板能力
==============================
区分进攻篮板(创造二次机会)和防守篮板(终结回合)

方法:
  总篮板排名: RPG(pace修正) x 稀缺性, 季后赛加权
  进攻篮板: ORB 单独排名 (创造力指标)
  防守篮板: DRB 单独排名 (终结力指标)
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

reg = pd.read_csv("data/nba100_career_all.csv")
reb = pd.read_csv("data/nba100_rebounds.csv")
po = pd.read_csv("data/nba100_playoffs.csv")

PACE, TEAMS = {}, {}
for y in range(1955, 1965): PACE[y], TEAMS[y] = 125, 9
for y in range(1965, 1975): PACE[y], TEAMS[y] = 110, 15
for y in range(1975, 1985): PACE[y], TEAMS[y] = 103, 23
for y in range(1985, 1995): PACE[y], TEAMS[y] = 95, 26
for y in range(1995, 2005): PACE[y], TEAMS[y] = 91, 29
for y in range(2005, 2015): PACE[y], TEAMS[y] = 95, 30
for y in range(2015, 2026): PACE[y], TEAMS[y] = 100, 30

# 合并篮板细分到常规赛数据
reb["year"] = reb["season"].str[:4].astype(int)
reg["year"] = reg["season"].str[:4].astype(int)

# 用 reb 数据 (有OREB/DREB)
reb["pace"] = reb["year"].map(PACE).fillna(97)
reb["teams"] = reb["year"].map(TEAMS).fillna(30)
reb["competition"] = (reb["teams"] / 30).pow(0.5)

# 填充缺失 (早期球员没有OREB/DREB分开)
# 对于缺失的, 按 30%进攻/70%防守 估算
reb["OREB"] = reb["OREB"].fillna(reb["REB"] * 0.3)
reb["DREB"] = reb["DREB"].fillna(reb["REB"] * 0.7)

# 每分钟
reb["RPM"] = reb["REB"] / reb["MIN"].replace(0, 1)
reb["ORPM"] = reb["OREB"] / reb["MIN"].replace(0, 1)
reb["DRPM"] = reb["DREB"] / reb["MIN"].replace(0, 1)

# 稀缺性
for col in ["REB", "OREB", "DREB"]:
    z_col = f"{col}_z"
    reb[z_col] = 0.0
    for year in reb["year"].unique():
        mask = reb["year"] == year
        d = reb.loc[mask, col]
        if d.std() > 0:
            reb.loc[mask, z_col] = (d - d.mean()) / d.std()

reb["reb_scarcity"] = 1 + reb["REB_z"] * 0.1

# 视角A: RPG(pace修正) x 稀缺性
reb["RPG_adj"] = reb["REB"] * (97 / reb["pace"])
reb["rebA"] = reb["RPG_adj"] * reb["reb_scarcity"]

# 视角C: RPM x 竞争强度 x 稀缺性
reb["rebC"] = reb["RPM"] * reb["competition"] * reb["reb_scarcity"]

# 生涯汇总
career = reb.groupby("player").agg({
    "REB": "mean", "OREB": "mean", "DREB": "mean",
    "GP": "sum", "MIN": "mean",
}).round(3).reset_index()
career.columns = ["player", "RPG", "OREB", "DREB", "GP", "MPG"]

# 巅峰+生涯
for view in ["rebA", "rebC"]:
    v_career = reb.groupby("player")[view].mean().round(4).reset_index()
    v_career.columns = ["player", f"{view}_career"]
    v_peak = reb.groupby("player")[view].apply(
        lambda x: x.nlargest(5).mean()).round(4).reset_index()
    v_peak.columns = ["player", f"{view}_peak"]
    career = career.merge(v_career, on="player").merge(v_peak, on="player")

# OREB/DREB 巅峰
for col in ["OREB", "DREB"]:
    peak = reb.groupby("player")[col].apply(
        lambda x: x.nlargest(5).mean()).round(2).reset_index()
    peak.columns = ["player", f"peak_{col}"]
    career = career.merge(peak, on="player")

# 季后赛经验加成
po_gp = po.groupby("player")["GP"].sum().reset_index()
po_gp.columns = ["player", "po_GP"]
career = career.merge(po_gp, on="player", how="left")
career["po_GP"] = career["po_GP"].fillna(0)

for view in ["rebA", "rebC"]:
    career[f"total_{view}"] = 0.6 * career[f"{view}_peak"] + 0.4 * career[f"{view}_career"]
    career[f"total_{view}"] *= (1 + np.log1p(career["po_GP"] / 82) * 0.1)
    career[f"total_{view}_rank"] = career[f"total_{view}"].rank(ascending=False).astype(int)

career["reb_median"] = career[["total_rebA_rank", "total_rebC_rank"]].median(axis=1)
career["reb_rank"] = career["reb_median"].rank().astype(int)

# OREB / DREB 单独排名
career["oreb_rank"] = career["peak_OREB"].rank(ascending=False).astype(int)
career["dreb_rank"] = career["peak_DREB"].rank(ascending=False).astype(int)

career = career.sort_values("reb_rank")

# ── 输出 ──
print("=" * 90)
print("REBOUNDING RANKING (101 players)")
print("=" * 90)
print("""
Total rebounds (RPG), pace-adjusted, era scarcity, playoff experience bonus.
OREB = offensive boards (二次进攻) | DREB = defensive boards (终结回合)
""")

print(f"{'Rk':>3s}  {'Player':28s} {'A':>3s} {'C':>3s}  "
      f"{'RPG':>5s} {'ORB':>4s} {'DRB':>4s} {'poGP':>4s}")
print("-" * 70)
for _, r in career.iterrows():
    print(f" {int(r['reb_rank']):3d}  {r['player']:28s} "
          f"{int(r['total_rebA_rank']):3d} {int(r['total_rebC_rank']):3d}  "
          f"{r['RPG']:4.1f}  {r['OREB']:3.1f}  {r['DREB']:3.1f}  {int(r['po_GP']):4d}")

# OREB/DREB 专项
print()
print("=" * 90)
print("OFFENSIVE REBOUNDING TOP 15 (创造二次进攻)")
print("=" * 90)
orb = career.sort_values("oreb_rank").head(15)
for _, r in orb.iterrows():
    print(f"  #{int(r['oreb_rank']):3d}  {r['player']:28s}  peak ORB={r['peak_OREB']:.1f}")

print()
print("=" * 90)
print("DEFENSIVE REBOUNDING TOP 15 (终结回合)")
print("=" * 90)
drb = career.sort_values("dreb_rank").head(15)
for _, r in drb.iterrows():
    print(f"  #{int(r['dreb_rank']):3d}  {r['player']:28s}  peak DRB={r['peak_DREB']:.1f}")

# 保存
career[["reb_rank", "player", "RPG", "OREB", "DREB",
        "oreb_rank", "dreb_rank", "po_GP",
        "total_rebA_rank", "total_rebC_rank"]].to_csv(
    "results/rebounding_ranking.csv", index=False)
print(f"\n-> results/rebounding_ranking.csv")
