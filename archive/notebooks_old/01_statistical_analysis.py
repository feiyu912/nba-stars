"""
Statistical Analysis: 让数据说话
=================================
1. 相关性分析 — 哪些指标是重复的？
2. PCA — 数据自己告诉我们几个维度、每个维度的权重
3. Era-adjusted Z-score — 球员在同时代的相对位置
4. Ridge回归 — 数据驱动的权重学习
5. 聚类分析 — 球员自然分组
6. 不确定性分析 — 排名的置信区间
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

# ── 1. 加载数据 ──
statnba = pd.read_csv("data/statnba_regular_targets.csv")
statnba_po = pd.read_csv("data/statnba_playoffs_targets.csv")
nba_api = pd.read_csv("data/nba_career_stats_real.csv")
databallr = pd.read_csv("data/databallr_raw.csv")
databallr["player_name"] = databallr["player_name"].replace("Luka Dončić", "Luka Doncic")

# 构建汇总表
nba_career = nba_api.groupby("player").agg({
    "PPG": "mean", "TS_pct": "mean", "APG": "mean", "GP": "sum",
}).round(4).reset_index()

era_map = {
    "Michael Jordan": "1990s", "LeBron James": "2010s",
    "Stephen Curry": "2010s", "Kevin Durant": "2010s",
    "Shaquille O'Neal": "2000s", "Kareem Abdul-Jabbar": "1970s",
    "Wilt Chamberlain": "1960s", "Kobe Bryant": "2000s",
    "James Harden": "2010s", "Luka Doncic": "2020s",
}
pace_map = {"1960s": 126, "1970s": 107, "1990s": 92, "2000s": 91, "2010s": 97, "2020s": 100}
lts_map = {"1960s": 0.490, "1970s": 0.510, "1990s": 0.535, "2000s": 0.530, "2010s": 0.555, "2020s": 0.572}

df = statnba[["player_en", "GP", "PPG", "RPG", "APG", "PER_base", "WS48", "USG", "OWS", "DWS", "WS"]].copy()
df = df.rename(columns={"PER_base": "PER"})

ts_map = dict(zip(nba_career["player"], nba_career["TS_pct"]))
df["TS_pct"] = df["player_en"].map(ts_map)
df["era"] = df["player_en"].map(era_map)
df["pace"] = df["era"].map(pace_map)
df["P100"] = (df["PPG"] * 100 / df["pace"]).round(2)
df["TS_plus"] = (df["TS_pct"] / df["era"].map(lts_map)).round(4)

# 季后赛
po_per = dict(zip(statnba_po["player_en"], statnba_po["PER_base"]))
df["PO_PER"] = df["player_en"].map(po_per)
df["PO_boost"] = ((df["PO_PER"] - df["PER"]) / df["PER"]).round(4)
df["PO_boost"] = df["PO_boost"].fillna(0)

# databallr 巅峰
for player in databallr["player_name"].unique():
    pdf = databallr[databallr["player_name"] == player].nlargest(5, "o_dpm")
    mask = df["player_en"] == player
    if mask.any():
        df.loc[mask, "db_O_DPM"] = pdf["o_dpm"].mean()
        df.loc[mask, "db_OnOff"] = pdf["netrtg_on_off"].mean()
        df.loc[mask, "db_PtsCreated"] = pdf["d_Points_Created_PerGame"].mean()

# 填充缺失
for col in ["WS48", "USG", "db_O_DPM", "db_OnOff", "db_PtsCreated"]:
    df[col] = df[col].fillna(df[col].median())

print("=" * 70)
print("STEP 1: CORRELATION ANALYSIS")
print("哪些指标在测量相同的东西？")
print("=" * 70)

analysis_cols = ["P100", "TS_plus", "PER", "WS48", "USG", "PO_boost"]
corr = df[analysis_cols].corr().round(3)
print(corr)
print()
print("解读:")
print("  - PER和WS48相关性:", corr.loc["PER", "WS48"], "→ 高度相关，测量类似的东西")
print("  - P100和PER相关性:", corr.loc["P100", "PER"], "→ 得分多的PER通常也高")
print("  - TS+和P100相关性:", corr.loc["TS_plus", "P100"], "→ 效率和产量的关系")
print()

# ═══════════════════════════════════════
# STEP 2: PCA — 让数据告诉我们真正的维度
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 2: PCA (Principal Component Analysis)")
print("数据自己告诉我们有几个真正独立的维度")
print("=" * 70)

pca_features = ["P100", "TS_plus", "PER", "WS48", "PPG", "APG", "USG", "PO_boost"]
X_pca = StandardScaler().fit_transform(df[pca_features])

pca = PCA()
pca.fit(X_pca)

print("\n方差解释比例 (每个主成分解释了多少信息):")
for i, (var, cum) in enumerate(zip(pca.explained_variance_ratio_,
                                     np.cumsum(pca.explained_variance_ratio_))):
    bar = "#" * int(var * 50)
    print(f"  PC{i+1}: {var:.3f} (累计: {cum:.3f})  {bar}")

print(f"\n结论: 前3个主成分解释了 {np.cumsum(pca.explained_variance_ratio_)[2]:.1%} 的信息")
print("  → 8个指标实际上只有 ~3 个独立维度")

print("\n各主成分的含义 (Loading矩阵):")
loadings = pd.DataFrame(
    pca.components_[:3].T,
    index=pca_features,
    columns=["PC1 (主维度)", "PC2 (第二维度)", "PC3 (第三维度)"]
).round(3)
print(loadings)
print()

# 解读
pc1_top = loadings["PC1 (主维度)"].abs().nlargest(3)
pc2_top = loadings["PC2 (第二维度)"].abs().nlargest(3)
print(f"PC1 主要由: {', '.join(pc1_top.index)} 驱动 → 这是'综合进攻效率'维度")
print(f"PC2 主要由: {', '.join(pc2_top.index)} 驱动 → 这是'产量/角色'维度")
print()

# PCA得分
pca3 = PCA(n_components=3)
pc_scores = pca3.fit_transform(X_pca)
df["PC1"] = pc_scores[:, 0]
df["PC2"] = pc_scores[:, 1]
df["PC3"] = pc_scores[:, 2]

# 用PCA自动权重排名
# 按方差比例加权
pca_weights = pca.explained_variance_ratio_[:3]
df["PCA_score"] = (pc_scores * pca_weights).sum(axis=1)
df["PCA_rank"] = df["PCA_score"].rank(ascending=False).astype(int)

print("PCA 自动排名 (数据驱动，零人工干预):")
print(df.sort_values("PCA_rank")[["PCA_rank", "player_en", "PC1", "PC2", "PC3", "PCA_score"]].round(3).to_string(index=False))
print()

# ═══════════════════════════════════════
# STEP 3: Era-Adjusted Z-Score
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 3: ERA-ADJUSTED ANALYSIS")
print("球员在自己时代有多突出？")
print("=" * 70)

# 用 databallr 全联盟数据计算每年的联盟分布
print("\n用 databallr 全联盟数据 (每年300-400人) 计算时代内Z-score:")

era_z_rows = []
for player in databallr["player_name"].unique():
    pdf = databallr[databallr["player_name"] == player]
    z_scores = []
    for _, row in pdf.iterrows():
        year = row["year"]
        year_data = databallr[databallr["year"] == year]
        # 这个球员在当年全联盟中的Z-score
        for col, label in [("d_Points_PerGame", "PPG_z"),
                           ("TS_pct", "TS_z"),
                           ("o_dpm", "ODPM_z"),
                           ("d_Points_Created_PerGame", "PtsC_z")]:
            mean = year_data[col].mean()
            std = year_data[col].std()
            if std > 0:
                z = (row[col] - mean) / std
            else:
                z = 0
            z_scores.append({"player": player, "year": year,
                             "metric": label, "z": round(z, 3)})
    era_z_rows.extend(z_scores)

ez = pd.DataFrame(era_z_rows)
ez_pivot = ez.pivot_table(index="player", columns="metric", values="z", aggfunc="mean").round(3)

print(ez_pivot.sort_values("PPG_z", ascending=False).to_string())
print()
print("解读: Z-score > 2 = 在同时代中属于前2.5%的极端异常值")
print("  → 这消除了时代差异，纯粹衡量'相对于同时代有多突出'")
print()

# 综合 era-Z score
ez_pivot["era_Z_total"] = ez_pivot.mean(axis=1).round(3)
ez_pivot["era_Z_rank"] = ez_pivot["era_Z_total"].rank(ascending=False).astype(int)
print("时代修正后排名:")
print(ez_pivot.sort_values("era_Z_rank")[["PPG_z", "TS_z", "ODPM_z", "PtsC_z",
                                           "era_Z_total", "era_Z_rank"]].to_string())
print()

# ═══════════════════════════════════════
# STEP 4: Ridge 回归 — 数据驱动权重
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 4: RIDGE REGRESSION")
print("让数据自己学习各指标的权重")
print("=" * 70)

# 用 PER 作为目标变量 (最被认可的综合效率指标)
features_ridge = ["P100", "TS_plus", "USG", "APG", "PO_boost"]
X_r = StandardScaler().fit_transform(df[features_ridge])
y_r = df["PER"].values

ridge = Ridge(alpha=1.0)
ridge.fit(X_r, y_r)

print("\nRidge 学到的标准化权重 (预测PER):")
ridge_weights = pd.Series(ridge.coef_, index=features_ridge).round(4)
ridge_weights_abs = ridge_weights.abs()
ridge_pct = (ridge_weights_abs / ridge_weights_abs.sum() * 100).round(1)

for f in features_ridge:
    bar = "#" * int(ridge_pct[f] / 2)
    print(f"  {f:12s}: {ridge_weights[f]:+.4f}  ({ridge_pct[f]:5.1f}%)  {bar}")

print(f"\n  R² = {ridge.score(X_r, y_r):.4f}")
print(f"\n结论: 数据告诉我们各指标对PER的贡献占比")
print(f"  最重要: {ridge_pct.idxmax()} ({ridge_pct.max()}%)")
print(f"  最不重要: {ridge_pct.idxmin()} ({ridge_pct.min()}%)")

# Ridge 排名
df["Ridge_score"] = ridge.predict(X_r)
df["Ridge_rank"] = df["Ridge_score"].rank(ascending=False).astype(int)
print("\nRidge 数据驱动排名:")
print(df.sort_values("Ridge_rank")[["Ridge_rank", "player_en", "Ridge_score"]].round(3).to_string(index=False))
print()

# ═══════════════════════════════════════
# STEP 5: Bootstrap 不确定性分析
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 5: BOOTSTRAP UNCERTAINTY")
print("每个排名有多确定？")
print("=" * 70)

n_boot = 5000
n_players = len(df)
all_features = ["P100", "TS_plus", "PER", "WS48", "PO_boost"]
X_boot = StandardScaler().fit_transform(df[all_features])

boot_ranks = np.zeros((n_boot, n_players))
np.random.seed(42)

for b in range(n_boot):
    # 随机扰动权重
    w = np.random.dirichlet(np.ones(len(all_features)) * 5)
    scores = X_boot @ w
    ranks = pd.Series(scores).rank(ascending=False).values
    boot_ranks[b] = ranks

# 统计每个球员的排名分布
print(f"\n{n_boot}次随机权重下的排名分布:")
print(f"{'球员':25s} {'中位排名':>8s} {'95%区间':>12s} {'排名稳定性':>10s}")
print("-" * 60)

stability = []
for i, player in enumerate(df["player_en"].values):
    ranks_i = boot_ranks[:, i]
    median_r = np.median(ranks_i)
    lo = np.percentile(ranks_i, 2.5)
    hi = np.percentile(ranks_i, 97.5)
    std_r = np.std(ranks_i)
    stability.append({"player": player, "median": median_r, "lo": lo, "hi": hi, "std": std_r})
    print(f"  {player:23s}  #{median_r:5.1f}    [{lo:.0f} - {hi:.0f}]     std={std_r:.2f}")

print()
stab = pd.DataFrame(stability).sort_values("median")
most_stable = stab.loc[stab["std"].idxmin(), "player"]
least_stable = stab.loc[stab["std"].idxmax(), "player"]
print(f"排名最确定: {most_stable} (无论怎么调权重都稳定)")
print(f"排名最不确定: {least_stable} (权重敏感)")

# ═══════════════════════════════════════
# STEP 6: 聚类分析 — 自然分组
# ═══════════════════════════════════════
print()
print("=" * 70)
print("STEP 6: CLUSTER ANALYSIS")
print("球员自然分成几个档次？")
print("=" * 70)

X_cluster = StandardScaler().fit_transform(df[["P100", "TS_plus", "PER", "WS48"]])
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df["tier"] = kmeans.fit_predict(X_cluster)

# 按平均PER给tier排序
tier_per = df.groupby("tier")["PER"].mean()
tier_order = tier_per.sort_values(ascending=False).index
tier_map = {old: new+1 for new, old in enumerate(tier_order)}
df["tier"] = df["tier"].map(tier_map)

print()
for tier in sorted(df["tier"].unique()):
    players = df[df["tier"] == tier].sort_values("PER", ascending=False)
    tier_label = {1: "Tier 1 (GOAT级)", 2: "Tier 2 (超巨级)", 3: "Tier 3 (巨星级)"}
    print(f"\n{tier_label.get(tier, f'Tier {tier}')}:")
    for _, row in players.iterrows():
        print(f"  {row['player_en']:25s}  PER={row['PER']:.1f}  P100={row['P100']:.1f}  WS48={row['WS48']:.3f}")

# ═══════════════════════════════════════
# FINAL: 所有方法对比
# ═══════════════════════════════════════
print()
print("=" * 70)
print("FINAL: ALL METHODS COMPARISON")
print("=" * 70)

compare = df[["player_en"]].copy()
compare["Manual_v6"] = df["player_en"].map(
    dict(zip(df.sort_values("PCA_rank")["player_en"],
             range(1, len(df)+1))))  # placeholder

# PCA rank
compare["PCA"] = df["PCA_rank"].values

# Ridge rank
compare["Ridge"] = df["Ridge_rank"].values

# Bootstrap median rank
boot_median = dict(zip([s["player"] for s in stability],
                        [s["median"] for s in stability]))
compare["Bootstrap_median"] = compare["player_en"].map(boot_median)

# Era-Z rank (only modern players)
ez_rank_map = dict(zip(ez_pivot.index, ez_pivot["era_Z_rank"]))
compare["Era_Z"] = compare["player_en"].map(ez_rank_map)

# Tier
compare["Tier"] = df["tier"].values

compare = compare.sort_values("PCA")
compare["PCA"] = compare["PCA"].astype(int)
compare["Ridge"] = compare["Ridge"].astype(int)

print(compare.to_string(index=False))
print()
print("如果多种方法给出相似排名 → 结果可信")
print("如果方法间分歧大 → 说明该球员的评价取决于'你更看重什么'")

# 保存
df.to_csv("results/statistical_analysis.csv", index=False)
print("\n-> Saved to results/statistical_analysis.csv")
