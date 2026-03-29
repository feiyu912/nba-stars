"""
Phase 3: Contextual Impact Model (Box Creation + Context TS)
=============================================================
改进：
  1. Box Creation = AST% x USG% x (TS+/100) → 区分playmaking质量
  2. Context TS = TS+ x sqrt(USG%) → 高使用率下的效率更有价值
  3. Ridge 回归替代手动权重（让数据学习）
  4. 敏感性分析：权重 +/-10% 的排名稳定性
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

# ── 1. 读取数据 ──
df = pd.read_csv("data/players_peak.csv")

# ── 2. 基础特征 ──
df["TS_plus"] = df["TS_pct"] / df["league_TS"]

pace_by_era = {
    "1960s": 126.0, "1970s": 107.0, "1990s": 92.0,
    "2000s": 91.0, "2010s": 97.0, "2020s": 100.0,
}
df["pace"] = df["era"].map(pace_by_era)
df["P100"] = df["PPG"] * (100.0 / df["pace"])

# ── 3. 高阶特征（Phase 3 核心） ──
# Box Creation: 衡量"创造得分"的综合能力
# 高AST + 高USG + 高效率 = 真正的进攻发动机
df["BoxCreation"] = df["AST_pct"] * df["USG_pct"] * (df["TS_plus"] / 100)

# Context TS: 在高使用率下保持效率 → 更有价值
# sqrt(USG%) 让使用率的加成是递减的（避免极端值主导）
df["ContextTS"] = df["TS_plus"] * np.sqrt(df["USG_pct"])

print("=" * 60)
print("高阶特征一览")
print("=" * 60)
print(df[["player", "P100", "TS_plus", "BoxCreation", "ContextTS", "PER", "WS_per48"]].round(3).to_string(index=False))
print()

# ── 4. 特征集 ──
features = ["P100", "TS_plus", "BoxCreation", "ContextTS", "PER", "WS_per48"]

print("=" * 60)
print("相关性矩阵")
print("=" * 60)
print(df[features].corr().round(3))
print()

# ── 5. 标准化 ──
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[features])

# ── 6. 加权评分（专家权重 v3） ──
# P100:        0.25 → 得分产量
# TS+:         0.15 → 基础效率
# BoxCreation: 0.15 → Playmaking质量
# ContextTS:   0.15 → 高负荷效率
# PER:         0.20 → 综合影响
# WS/48:       0.10 → 胜利贡献
weights_v3 = np.array([0.25, 0.15, 0.15, 0.15, 0.20, 0.10])
df["Score_v3"] = X_scaled @ weights_v3

# ── 7. Ridge 回归（让数据自己学） ──
# 目标变量：用 PER 作为"综合进攻评价"的proxy
# 注意：这里是 demonstration，实际应用需外部目标变量
features_ridge = ["P100", "TS_plus", "BoxCreation", "ContextTS"]
X_ridge = StandardScaler().fit_transform(df[features_ridge])
y_ridge = df["PER"].values  # proxy target

ridge = Ridge(alpha=1.0)
ridge.fit(X_ridge, y_ridge)

print("=" * 60)
print("Ridge 回归学到的权重")
print("=" * 60)
for f, c in zip(features_ridge, ridge.coef_):
    print(f"  {f:15s}: {c:+.4f}")
print(f"  {'intercept':15s}: {ridge.intercept_:.4f}")
print()

# Ridge 产出的排名
df["Score_ridge"] = ridge.predict(X_ridge)

# ── 8. 最终排名（v3加权） ──
df["Rank"] = df["Score_v3"].rank(ascending=False).astype(int)
df = df.sort_values("Rank")

print("=" * 60)
print("Phase 3 Final Ranking")
print("=" * 60)
cols = ["Rank", "player", "era", "P100", "TS_plus", "BoxCreation", "ContextTS", "Score_v3"]
result = df[cols].copy()
for c in ["P100", "BoxCreation", "ContextTS", "Score_v3"]:
    result[c] = result[c].round(3)
result["TS_plus"] = result["TS_plus"].round(3)
print(result.to_string(index=False))

# ── 9. Sanity Check ──
print()
print("=" * 60)
print("Sanity Check")
print("=" * 60)
top5 = set(df.nsmallest(5, "Rank")["player"])
expected = {"Michael Jordan", "LeBron James", "Stephen Curry", "Kevin Durant", "Shaquille O'Neal"}
overlap = top5 & expected
print(f"前5名命中: {len(overlap)}/5 -> {overlap}")

# ── 10. 敏感性分析 ──
print()
print("=" * 60)
print("敏感性分析 (Sensitivity Analysis)")
print("权重 +/-10% 对排名的影响")
print("=" * 60)

base_weights = weights_v3.copy()
player_ranks = {}

for i, fname in enumerate(features):
    for direction in [+0.10, -0.10]:
        w = base_weights.copy()
        w[i] *= (1 + direction)
        w = w / w.sum()  # 归一化
        scores = X_scaled @ w
        ranks = pd.Series(scores).rank(ascending=False).astype(int).values
        label = f"{fname} {'+'if direction>0 else ''}{direction*100:.0f}%"
        player_ranks[label] = ranks

sensitivity_df = pd.DataFrame(player_ranks, index=df["player"])
# 计算每个球员排名的标准差
sensitivity_df["rank_std"] = sensitivity_df.std(axis=1)
print(sensitivity_df.round(2).to_string())
print()
max_unstable = sensitivity_df["rank_std"].idxmax()
print(f"排名最不稳定的球员: {max_unstable} (std={sensitivity_df.loc[max_unstable, 'rank_std']:.2f})")

# ── 11. 三版对比 ──
print()
print("=" * 60)
print("三版排名演化对比")
print("=" * 60)
v1 = pd.read_csv("results/ranking_v1.csv")[["player", "Rank"]].rename(columns={"Rank": "v1"})
v2 = pd.read_csv("results/ranking_v2.csv")[["player", "Rank"]].rename(columns={"Rank": "v2"})
v3 = df[["player", "Rank"]].rename(columns={"Rank": "v3"})

compare = v3.merge(v1, on="player").merge(v2, on="player")[["player", "v1", "v2", "v3"]]
compare = compare.sort_values("v3")
print(compare.to_string(index=False))

# ── 12. 保存 ──
output = df[["Rank", "player", "era", "P100", "TS_plus", "BoxCreation", "ContextTS", "PER", "WS_per48", "Score_v3"]]
output.to_csv("results/ranking_v3.csv", index=False)
print()
print("-> 结果已保存至 results/ranking_v3.csv")
