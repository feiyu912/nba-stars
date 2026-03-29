"""
Phase 1-3 Complete Model (Real Data)
=====================================
使用真实数据重跑所有阶段:
  Phase 1: P100 + TS+ + AST% (基线)
  Phase 2: + PER + WS/48 (影响力)
  Phase 3: + BoxCreation + ContextTS + BPM (完整版)

数据来源: data/players_final.csv
  - PPG/TS%: NBA API (stats.nba.com)
  - PER: Wikipedia
  - WS/48, USG%, AST%, BPM: Basketball-Reference.com
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

df = pd.read_csv("data/players_final.csv")

# ==============================
# PHASE 1: Baseline (3 features)
# ==============================
print("=" * 70)
print("PHASE 1: Baseline Model (P100 + TS+ + AST%)")
print("=" * 70)

features_1 = ["P100", "TS_plus", "AST_pct"]
scaler_1 = StandardScaler()
X1 = scaler_1.fit_transform(df[features_1])

weights_1 = np.array([0.50, 0.30, 0.20])
df["score_v1"] = X1 @ weights_1
df["rank_v1"] = df["score_v1"].rank(ascending=False).astype(int)

result_1 = df.sort_values("rank_v1")[["rank_v1", "player", "P100", "TS_plus", "AST_pct", "score_v1"]].copy()
result_1["score_v1"] = result_1["score_v1"].round(4)
result_1["TS_plus"] = result_1["TS_plus"].round(3)
print(result_1.to_string(index=False))
print()

# ==============================
# PHASE 2: + PER + WS/48
# ==============================
print("=" * 70)
print("PHASE 2: Era-Adjusted + Impact (P100 + TS+ + AST% + PER + WS/48)")
print("=" * 70)

features_2 = ["P100", "TS_plus", "AST_pct", "PER", "WS_per48"]
scaler_2 = StandardScaler()
X2 = scaler_2.fit_transform(df[features_2])

weights_2 = np.array([0.30, 0.25, 0.10, 0.20, 0.15])
df["score_v2"] = X2 @ weights_2
df["rank_v2"] = df["score_v2"].rank(ascending=False).astype(int)

result_2 = df.sort_values("rank_v2")[["rank_v2", "player", "P100", "TS_plus", "PER", "WS_per48", "score_v2"]].copy()
result_2["score_v2"] = result_2["score_v2"].round(4)
result_2["TS_plus"] = result_2["TS_plus"].round(3)
print(result_2.to_string(index=False))
print()

# ==============================
# PHASE 3: Full Context Model
# ==============================
print("=" * 70)
print("PHASE 3: Full Contextual Model (+ BoxCreation + ContextTS + BPM)")
print("=" * 70)

features_3 = ["P100", "TS_plus", "BoxCreation", "ContextTS", "PER", "WS_per48", "BPM"]
scaler_3 = StandardScaler()
X3 = scaler_3.fit_transform(df[features_3])

#   P100:        0.20  得分产量
#   TS+:         0.10  基础效率
#   BoxCreation: 0.10  Playmaking质量
#   ContextTS:   0.10  高负荷效率
#   PER:         0.20  综合效率
#   WS/48:       0.15  胜利贡献
#   BPM:         0.15  整体影响力
weights_3 = np.array([0.20, 0.10, 0.10, 0.10, 0.20, 0.15, 0.15])
df["score_v3"] = X3 @ weights_3
df["rank_v3"] = df["score_v3"].rank(ascending=False).astype(int)

result_3 = df.sort_values("rank_v3")[["rank_v3", "player", "era", "P100", "TS_plus", "PER", "WS_per48", "BPM", "score_v3"]].copy()
result_3["score_v3"] = result_3["score_v3"].round(4)
result_3["TS_plus"] = result_3["TS_plus"].round(3)
print(result_3.to_string(index=False))
print()

# ==============================
# Ridge Regression (数据驱动)
# ==============================
print("=" * 70)
print("RIDGE REGRESSION (BPM as target, auto-learned weights)")
print("=" * 70)

features_r = ["P100", "TS_plus", "BoxCreation", "ContextTS", "PER", "WS_per48"]
Xr = StandardScaler().fit_transform(df[features_r])
yr = df["BPM"].values

ridge = Ridge(alpha=1.0)
ridge.fit(Xr, yr)

for f, c in zip(features_r, ridge.coef_):
    print(f"  {f:15s}: {c:+.4f}")
print(f"  {'intercept':15s}: {ridge.intercept_:.4f}")

df["score_ridge"] = ridge.predict(Xr)
df["rank_ridge"] = df["score_ridge"].rank(ascending=False).astype(int)
print()
result_r = df.sort_values("rank_ridge")[["rank_ridge", "player", "score_ridge"]].copy()
result_r["score_ridge"] = result_r["score_ridge"].round(4)
print(result_r.to_string(index=False))
print()

# ==============================
# EVOLUTION COMPARISON
# ==============================
print("=" * 70)
print("RANKING EVOLUTION (v1 -> v2 -> v3 -> Ridge)")
print("=" * 70)
compare = df.sort_values("rank_v3")[["player", "rank_v1", "rank_v2", "rank_v3", "rank_ridge"]].copy()
print(compare.to_string(index=False))
print()

# ==============================
# SENSITIVITY ANALYSIS
# ==============================
print("=" * 70)
print("SENSITIVITY ANALYSIS (Phase 3, weights +/-10%)")
print("=" * 70)
base_w = weights_3.copy()
sens_ranks = {}

for i, fname in enumerate(features_3):
    for d in [+0.10, -0.10]:
        w = base_w.copy()
        w[i] *= (1 + d)
        w = w / w.sum()
        scores = X3 @ w
        ranks = pd.Series(scores).rank(ascending=False).astype(int).values
        label = f"{fname} {'+' if d > 0 else ''}{d*100:.0f}%"
        sens_ranks[label] = ranks

sens_df = pd.DataFrame(sens_ranks, index=df["player"])
sens_df["std"] = sens_df.std(axis=1).round(2)
print(sens_df.to_string())

# ==============================
# SAVE ALL RESULTS
# ==============================
final = df.sort_values("rank_v3")
final[["rank_v3", "player", "era", "PPG", "P100", "TS_pct", "TS_plus",
       "PER", "WS_per48", "USG_pct", "AST_pct", "BPM", "OBPM",
       "BoxCreation", "ContextTS", "score_v1", "score_v2", "score_v3",
       "score_ridge"]].to_csv("results/ranking_real_data.csv", index=False)

print()
print("-> Results saved to results/ranking_real_data.csv")
