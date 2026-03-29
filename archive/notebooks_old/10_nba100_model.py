"""
NBA 101-Player Scoring Model
==============================
Layer 1: 全101人 (NBA API基础数据 → TS%, PPG, 全面性)
Layer 2: 56人现代球员 (databallr高阶 → O-DPM, On-Off, pt_adj_rTS)

数据: 1541赛季(NBA API) + 641赛季(databallr)
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# ── 1. 加载数据 ──
nba = pd.read_csv("data/nba100_career_all.csv")
db = pd.read_csv("data/nba100_databallr.csv")
db["player_name"] = db["player_name"].replace({
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
})

print(f"NBA API: {nba['player'].nunique()} players, {len(nba)} seasons")
print(f"databallr: {db['player_name'].nunique()} players, {len(db)} seasons")

# ── 2. 生涯汇总 (NBA API) ──
career = nba.groupby("player").agg({
    "PPG": "mean", "RPG": "mean", "APG": "mean",
    "SPG": "mean", "BPG": "mean", "TOV": "mean",
    "TS_pct": "mean", "FG_PCT": "mean", "FT_PCT": "mean",
    "MIN": "mean", "GP": "sum",
    "season": ["count", "min", "max"],
}).round(4)
career.columns = ["PPG", "RPG", "APG", "SPG", "BPG", "TOV",
                   "TS_pct", "FG_pct", "FT_pct", "MPG", "GP",
                   "seasons", "first", "last"]
career = career.reset_index()

# 时代
def get_era(first, last):
    # 用生涯中点判断时代
    start = int(first[:4])
    end = int(last[:4])
    mid = (start + end) // 2
    if mid < 1965: return "1950-60s"
    elif mid < 1980: return "1970s"
    elif mid < 1995: return "1980-90s"
    elif mid < 2010: return "2000s"
    else: return "2010s+"

career["era"] = career.apply(lambda r: get_era(r["first"], r["last"]), axis=1)

# 联盟平均TS%
era_ts = {"1950-60s": 0.480, "1970s": 0.510, "1980-90s": 0.535,
           "2000s": 0.535, "2010s+": 0.565}
career["league_TS"] = career["era"].map(era_ts)
career["TS_plus"] = (career["TS_pct"] / career["league_TS"]).round(4)

# Pace修正
era_pace = {"1950-60s": 120, "1970s": 107, "1980-90s": 95,
             "2000s": 93, "2010s+": 99}
career["pace"] = career["era"].map(era_pace)
career["P100"] = (career["PPG"] * 100 / career["pace"]).round(2)

# 填补缺失 (早期球员没有STL/BLK/TOV)
for col in ["SPG", "BPG", "TOV"]:
    career[col] = career[col].fillna(career[col].median())

# ── 3. databallr 生涯汇总 ──
db_career = db.groupby("player_name").agg({
    "o_dpm": "mean", "d_dpm": "mean", "dpm": "mean",
    "netrtg_on_off": "mean", "rTSPct": "mean",
    "d_Points_Created_PerGame": "mean", "d_Points_Per100": "mean",
    "pt_adj_rTS": "mean", "playtype_diff": "mean",
    "year": "count",
}).round(3)
db_career.columns = ["o_dpm", "d_dpm", "dpm", "onoff", "rTS",
                       "PtsCreated", "P100_db", "pt_adj_rTS", "playtype_diff",
                       "db_seasons"]
db_career = db_career.reset_index().rename(columns={"player_name": "player"})

# 合并
career = career.merge(db_career, on="player", how="left")

print(f"\nCombined: {len(career)} players")
print(f"  With databallr: {career['o_dpm'].notna().sum()}")
print(f"  Without (pre-2001): {career['o_dpm'].isna().sum()}")

# ═══════════════════════════════════════
# LAYER 1: Universal (101 players)
# ═══════════════════════════════════════
print()
print("=" * 70)
print("LAYER 1: UNIVERSAL SCORING RANKING (all 101 players)")
print("Features: P100, TS+, APG, RPG, SPG, BPG")
print("=" * 70)

L1_features = ["P100", "TS_plus", "APG", "RPG"]
X1 = StandardScaler().fit_transform(career[L1_features])

# PCA 自动权重
pca = PCA(n_components=len(L1_features))
pca.fit(X1)
pc_scores = pca.transform(X1)
pca_weights = pca.explained_variance_ratio_
career["L1_score"] = (pc_scores * pca_weights).sum(axis=1)
career["L1_rank"] = career["L1_score"].rank(ascending=False).astype(int)

print(f"\nPCA variance explained: {pca.explained_variance_ratio_.round(3)}")
print(f"Loadings:")
for i, feat in enumerate(L1_features):
    print(f"  {feat:10s}: PC1={pca.components_[0][i]:+.3f}  PC2={pca.components_[1][i]:+.3f}")

print(f"\n{'Rank':>4s}  {'Player':28s} {'Era':10s} {'PPG':>5s} {'P100':>5s} {'TS+':>5s} {'APG':>4s} {'RPG':>4s} {'Score':>6s}")
print("-" * 78)
for _, r in career.sort_values("L1_rank").head(30).iterrows():
    print(f"  {int(r['L1_rank']):3d}  {r['player']:28s} {r['era']:10s} "
          f"{r['PPG']:5.1f} {r['P100']:5.1f} {r['TS_plus']:5.3f} "
          f"{r['APG']:4.1f} {r['RPG']:4.1f} {r['L1_score']:+6.3f}")

# ═══════════════════════════════════════
# LAYER 2: Modern (56 players with databallr)
# ═══════════════════════════════════════
print()
print("=" * 70)
print("LAYER 2: MODERN PLAYERS (with O-DPM, On-Off, pt_adj_rTS)")
print("=" * 70)

modern = career[career["o_dpm"].notna()].copy()
L2_features = ["P100", "TS_plus", "o_dpm", "onoff", "dpm"]

# 填充 pt_adj_rTS 缺失
for col in ["pt_adj_rTS", "playtype_diff"]:
    modern[col] = modern[col].fillna(modern[col].median())

X2 = StandardScaler().fit_transform(modern[L2_features])
pca2 = PCA(n_components=len(L2_features))
pc2 = pca2.transform(pca2.fit(X2).transform(X2).dot(np.eye(len(L2_features))))
# 简单用加权
w2 = np.array([0.15, 0.10, 0.25, 0.20, 0.30])  # DPM最重
modern["L2_score"] = StandardScaler().fit_transform(modern[L2_features]) @ w2
modern["L2_rank"] = modern["L2_score"].rank(ascending=False).astype(int)

print(f"\n{'Rank':>4s}  {'Player':28s} {'O-DPM':>6s} {'D-DPM':>6s} {'DPM':>5s} {'On-Off':>7s} {'Score':>6s}")
print("-" * 72)
for _, r in modern.sort_values("L2_rank").head(30).iterrows():
    print(f"  {int(r['L2_rank']):3d}  {r['player']:28s} "
          f"{r['o_dpm']:+5.2f}  {r['d_dpm']:+5.2f}  {r['dpm']:+4.2f}  "
          f"{r['onoff']:+6.2f}  {r['L2_score']:+5.3f}")

# ═══════════════════════════════════════
# TIER ANALYSIS (Clustering)
# ═══════════════════════════════════════
print()
print("=" * 70)
print("TIER ANALYSIS: 101 players clustered into tiers")
print("=" * 70)

X_cluster = StandardScaler().fit_transform(career[["P100", "TS_plus", "APG", "RPG"]])
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
career["cluster"] = kmeans.fit_predict(X_cluster)

# 排序 tier
tier_scores = career.groupby("cluster")["L1_score"].mean().sort_values(ascending=False)
tier_map = {old: new+1 for new, old in enumerate(tier_scores.index)}
career["Tier"] = career["cluster"].map(tier_map)

tier_labels = {1: "GOAT", 2: "MVP", 3: "All-NBA", 4: "All-Star", 5: "Star"}
for tier in sorted(career["Tier"].unique()):
    players = career[career["Tier"] == tier].sort_values("L1_rank")
    label = tier_labels.get(tier, f"Tier {tier}")
    print(f"\n--- Tier {tier} ({label}) ---")
    for _, r in players.iterrows():
        db_flag = "+" if pd.notna(r.get("o_dpm")) else " "
        print(f"  #{int(r['L1_rank']):3d} {db_flag} {r['player']:28s} {r['era']:10s} "
              f"PPG={r['PPG']:5.1f}  TS+={r['TS_plus']:.3f}")

# ═══════════════════════════════════════
# SAVE
# ═══════════════════════════════════════
career.sort_values("L1_rank").to_csv("results/nba100_ranking.csv", index=False)
modern.sort_values("L2_rank").to_csv("results/nba100_modern_ranking.csv", index=False)

print(f"\n-> results/nba100_ranking.csv (all 101)")
print(f"-> results/nba100_modern_ranking.csv (56 modern)")
