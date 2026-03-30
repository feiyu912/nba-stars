"""
Defense Ranking: 防守能力
=========================
谁的防守影响力最大？

方法 (同 Scoring/Playmaking 框架):
  表1: 防守产出排名
    视角A: (SPG+BPG)(pace修正) x 稀缺性
    视角C: 每分钟(SPG+BPG) x 竞争强度 x 稀缺性
    季后赛3x, 巅峰60%+生涯40%, 中位数

  表2: 防守影响力 (Ridge预测D-DPM)
    用53人的D-DPM训练, era Z-score特征, 预测101人

注意: SPG/BPG 1973年前没有, 11名球员缺失 → 用中位数填充(会偏低)
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import warnings
warnings.filterwarnings('ignore')

reg = pd.read_csv("data/nba100_career_all.csv")
po = pd.read_csv("data/nba100_playoffs.csv")
db = pd.read_csv("data/nba100_databallr.csv")
db["player_name"] = db["player_name"].replace({
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
})

PACE, TEAMS = {}, {}
for y in range(1955, 1965): PACE[y], TEAMS[y] = 125, 9
for y in range(1965, 1975): PACE[y], TEAMS[y] = 110, 15
for y in range(1975, 1985): PACE[y], TEAMS[y] = 103, 23
for y in range(1985, 1995): PACE[y], TEAMS[y] = 95, 26
for y in range(1995, 2005): PACE[y], TEAMS[y] = 91, 29
for y in range(2005, 2015): PACE[y], TEAMS[y] = 95, 30
for y in range(2015, 2026): PACE[y], TEAMS[y] = 100, 30

PLAYOFF_MULTIPLIER = 3

def process_defense(df):
    df = df.copy()
    df["year"] = df["season"].str[:4].astype(int)
    df["pace"] = df["year"].map(PACE).fillna(97)
    df["teams"] = df["year"].map(TEAMS).fillna(30)
    df["competition"] = (df["teams"] / 30).pow(0.5)

    df["SPG"] = df["SPG"].fillna(df["SPG"].median())
    df["BPG"] = df["BPG"].fillna(df["BPG"].median())

    # 防守产出: STL + BLK (不同技能, 同等重要)
    df["def_output"] = df["SPG"] + df["BPG"]
    df["def_pm"] = df["def_output"] / df["MIN"].replace(0, 1)

    # 稀缺性
    year_stats = df.groupby("year")["def_output"].agg(["mean", "std"]).reset_index()
    year_stats.columns = ["year", "y_mean", "y_std"]
    df = df.merge(year_stats, on="year", how="left")
    df["y_std"] = df["y_std"].replace(0, 1)
    df["def_zscore"] = (df["def_output"] - df["y_mean"]) / df["y_std"]
    df["scarcity"] = 1 + df["def_zscore"] * 0.1

    # 视角A: 防守产出(pace修正) x 稀缺性
    df["def_adj"] = df["def_output"] * (97 / df["pace"])
    df["defA"] = df["def_adj"] * df["scarcity"]

    # 视角C: 每分钟 x 竞争强度 x 稀缺性
    df["defC"] = df["def_pm"] * df["competition"] * df["scarcity"]

    return df

def summarize_def(df, prefix):
    result = df.groupby("player").agg({
        "SPG": "mean", "BPG": "mean", "def_output": "mean",
        "GP": "sum", "MIN": "mean",
    }).round(3).reset_index()
    result.columns = ["player", f"{prefix}_SPG", f"{prefix}_BPG",
                       f"{prefix}_def", f"{prefix}_GP", f"{prefix}_MPG"]

    for view in ["defA", "defC"]:
        career_v = df.groupby("player")[view].mean().round(4).reset_index()
        career_v.columns = ["player", f"{prefix}_{view}_career"]
        peak_v = df.groupby("player")[view].apply(
            lambda x: x.nlargest(5).mean()).round(4).reset_index()
        peak_v.columns = ["player", f"{prefix}_{view}_peak"]
        result = result.merge(career_v, on="player").merge(peak_v, on="player")

    return result

# 处理 (季后赛数据没有SPG/BPG, 只用常规赛的防守指标)
reg = process_defense(reg)

reg_sum = summarize_def(reg, "reg")
career = reg_sum.copy()

# 季后赛场次用来加权 (防守指标用常规赛, 但打过更多季后赛说明防守经得起考验)
po_gp = po.groupby("player")["GP"].sum().reset_index()
po_gp.columns = ["player", "po_GP"]
career = career.merge(po_gp, on="player", how="left")
career["po_GP"] = career["po_GP"].fillna(0)

# 巅峰 + 生涯
for view in ["defA", "defC"]:
    career[f"total_{view}"] = 0.6 * career[f"reg_{view}_peak"] + 0.4 * career[f"reg_{view}_career"]
    # 季后赛经验加成: 打过越多季后赛 → 说明防守被信任
    # 温和加成: 1 + log(1 + po_GP/82) * 0.1
    import numpy as np
    career[f"total_{view}"] *= (1 + np.log1p(career["po_GP"] / 82) * 0.1)
    career[f"total_{view}_rank"] = career[f"total_{view}"].rank(ascending=False).astype(int)

career["def_median"] = career[["total_defA_rank", "total_defC_rank"]].median(axis=1)
career["def_rank"] = career["def_median"].rank().astype(int)

# ── 表2: 防守影响力 (Ridge预测D-DPM) ──
db_c = db.groupby("player_name").agg({"d_dpm": "mean"}).round(3).reset_index()
db_c.columns = ["player", "d_dpm"]
career = career.merge(db_c, on="player", how="left")

# era Z-score 特征
for col in ["SPG", "BPG"]:
    z_col = f"{col}_era_z"
    reg[z_col] = 0.0
    for year in reg["year"].unique():
        mask = reg["year"] == year
        year_data = reg.loc[mask, col].dropna()
        if year_data.std() > 0:
            reg.loc[mask, z_col] = (reg.loc[mask, col] - year_data.mean()) / year_data.std()

era_z = reg.groupby("player").agg({
    "SPG_era_z": "mean", "BPG_era_z": "mean", "RPG": "mean",
}).round(4).reset_index()

peak_def_z = reg.groupby("player")["SPG_era_z"].apply(
    lambda x: x.nlargest(5).mean()).round(4).reset_index()
peak_def_z.columns = ["player", "peak_SPG_z"]

career = career.merge(era_z, on="player", how="left")
career = career.merge(peak_def_z, on="player", how="left")

features = ["SPG_era_z", "BPG_era_z", "RPG", "peak_SPG_z"]
train_mask = career["d_dpm"].notna()
for f in features:
    career[f] = career[f].fillna(career[f].median())

scaler = StandardScaler()
X_all = scaler.fit_transform(career[features])
X_tr = X_all[train_mask.values]
ridge = Ridge(alpha=2.0).fit(X_tr, career.loc[train_mask, "d_dpm"].values)
career["def_impact_score"] = ridge.predict(X_all)
career["def_impact_rank"] = career["def_impact_score"].rank(ascending=False).astype(int)

# ── 输出 ──
career = career.sort_values("def_rank")

print("=" * 90)
print("DEFENSE RANKING: 防守产出 (101 players)")
print("=" * 90)
print("""
防守产出 = STL + BLK (抢断 + 盖帽)
  A = (SPG+BPG)(pace修正) x 稀缺性
  C = (SPG+BPG)/MIN x 竞争强度 x 稀缺性
  季后赛3x | 巅峰60%+生涯40% | 中位数

注: 1973年前无STL/BPG数据, 11人用中位数填充(会偏低)
""")

print(f"{'Rk':>3s}  {'Player':28s} {'A':>3s} {'C':>3s}  "
      f"{'SPG':>4s} {'BPG':>4s} {'S+B':>4s} {'poGP':>4s}")
print("-" * 72)
for _, r in career.iterrows():
    print(f" {int(r['def_rank']):3d}  {r['player']:28s} "
          f"{int(r['total_defA_rank']):3d} {int(r['total_defC_rank']):3d}  "
          f"{r['reg_SPG']:3.1f}  {r['reg_BPG']:3.1f}  {r['reg_def']:3.1f}  {int(r['po_GP']):4d}")

# 表2
print()
print("=" * 90)
print("DEFENSIVE IMPACT: Ridge预测D-DPM (101 players)")
print("=" * 90)

impact = career.sort_values("def_impact_rank")
print(f"\n{'Rk':>3s}  {'Player':28s} {'Pred':>6s} {'Actual':>7s}  "
      f"{'SPG':>4s} {'BPG':>4s} {'RPG':>4s}")
print("-" * 65)
for _, r in impact.head(30).iterrows():
    actual = f"{r['d_dpm']:+5.2f}*" if pd.notna(r["d_dpm"]) else "    - "
    print(f" {int(r['def_impact_rank']):3d}  {r['player']:28s} "
          f"{r['def_impact_score']:+5.2f}  {actual}  "
          f"{r['reg_SPG']:3.1f}  {r['reg_BPG']:3.1f}  {r['RPG']:4.1f}")

# 保存
career[["def_rank", "player", "reg_SPG", "reg_BPG", "reg_def",
        "po_GP", "total_defA_rank", "total_defC_rank",
        "def_impact_rank", "def_impact_score", "d_dpm"]].to_csv(
    "results/defense_ranking.csv", index=False)
print(f"\n-> results/defense_ranking.csv")

# 交叉对比
print()
print("=" * 90)
print("CROSS-TABLE: Scoring vs Defense")
print("=" * 90)

scoring = pd.read_csv("results/scoring_ranking.csv")
cross = career[["player", "def_rank"]].merge(
    scoring[["player", "scoring_rank"]], on="player", how="left")
cross = cross.sort_values("def_rank")

print(f"\n{'Player':28s} {'Score':>5s} {'Def':>5s}  {'Type'}")
print("-" * 55)
for _, r in cross.head(25).iterrows():
    sr = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    dr = int(r["def_rank"])
    if sr <= 20 and dr <= 20: t = "Two-way star"
    elif sr <= 20: t = "Scorer who defends"
    elif dr <= 20: t = "Defensive specialist"
    else: t = ""
    print(f"  {r['player']:28s} #{sr:3d}  #{dr:3d}   {t}")
