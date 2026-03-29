"""
Phase 1: Baseline Scoring Impact Model (MVP)
=============================================
目标：用 3 个核心特征（PPG, TS+, AST%）构建第一版排名
验证标准：乔丹/詹姆斯/库里/杜兰特 应出现在前列
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ── 1. 读取数据 ──
df = pd.read_csv("data/players_peak.csv")

# ── 2. 特征工程 ──
# TS+: 相对于联盟平均的效率（>1 = 高于平均）
df["TS_plus"] = df["TS_pct"] / df["league_TS"]

# ── 3. 相关性分析（检查共线性） ──
features = ["PPG", "TS_plus", "AST_pct"]
print("=" * 50)
print("相关性矩阵 (Correlation Matrix)")
print("=" * 50)
print(df[features].corr().round(3))
print()

# ── 4. 标准化 ──
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[features])

# ── 5. 加权评分 ──
# 权重设计理由：
#   PPG  0.50 → 得分能力是"最强得分手"的核心
#   TS+  0.30 → 效率区分"高效"与"高产低效"
#   AST  0.20 → 组织能力作为辅助维度
weights = np.array([0.50, 0.30, 0.20])
df["Score"] = X_scaled @ weights

# ── 6. 排名 ──
df["Rank"] = df["Score"].rank(ascending=False).astype(int)
df = df.sort_values("Rank")

# ── 7. 输出结果 ──
print("=" * 50)
print("Phase 1 Baseline Ranking (MVP)")
print("=" * 50)
result = df[["Rank", "player", "PPG", "TS_plus", "AST_pct", "Score"]].copy()
result["TS_plus"] = result["TS_plus"].round(3)
result["Score"] = result["Score"].round(4)
print(result.to_string(index=False))

# ── 8. Sanity Check ──
print()
print("=" * 50)
print("Sanity Check")
print("=" * 50)
top4 = set(df.nsmallest(4, "Rank")["player"])
expected_top = {"Michael Jordan", "LeBron James", "Stephen Curry", "Kevin Durant"}
overlap = top4 & expected_top
print(f"前4名中命中预期球员: {len(overlap)}/4 → {overlap}")
if len(overlap) >= 3:
    print("[PASS] 基本合理，可以进入 Phase 2")
else:
    print("[FAIL] 需要检查权重或数据")

# ── 9. 保存结果 ──
output = df[["Rank", "player", "era", "PPG", "TS_plus", "AST_pct", "Score"]].copy()
output.to_csv("results/ranking_v1.csv", index=False)
print()
print("→ 结果已保存至 results/ranking_v1.csv")
