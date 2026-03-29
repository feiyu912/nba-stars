"""
Outcome-Driven Model: 以赢球为导向
====================================
核心思想:
  不是问"谁数据好看"
  而是问"谁的数据真正转化成了赢球"

方法:
  目标变量: On-Off 净效率差 (球员在场vs不在场，球队赢多少)
  → 这就是"最终比赛结果的转化"
  → 用各项进攻数据去预测它
  → 哪个指标预测力最强，哪个就最"有用"

数据: databallr API (2001-2026), 110个球员-赛季样本
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, Lasso, LinearRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# ── 1. 加载全量 databallr 数据 ──
df = pd.read_csv("data/databallr_raw.csv")
df["player_name"] = df["player_name"].replace("Luka Dončić", "Luka Doncic")

print("=" * 70)
print("THE CORE QUESTION")
print("=" * 70)
print("""
我们有各种进攻数据: PPG, TS%, PtsCreated, O-DPM...
但问题是: 这些数据真的转化成赢球了吗？

验证方法:
  目标变量 = On-Off 净效率差 (netrtg_on_off)
  含义: 球员在场时球队每100回合比不在场时多赢多少分
  这是最接近"真实比赛结果转化"的指标

样本: {n} 个球员-赛季 (8名球员, 2001-2026)
""".format(n=len(df)))

# ── 2. 特征 vs 赢球的相关性 ──
print("=" * 70)
print("STEP 1: 各指标与赢球(On-Off)的相关性")
print("哪些数据真正转化成了比赛结果？")
print("=" * 70)

features = {
    "d_Points_PerGame": "PPG (场均得分)",
    "d_Points_Per100": "P100 (每100回合得分)",
    "TS_pct": "TS% (真实命中率)",
    "rTSPct": "rTS% (相对效率)",
    "d_Points_Created_PerGame": "PtsCreated (创造得分)",
    "d_Points_Created_Per100": "PtsCreated/100",
    "o_dpm": "O-DPM (进攻影响力)",
    "dpm": "DPM (综合影响力)",
    "d_Assists_PerGame": "APG (助攻)",
}

target = "netrtg_on_off"

print(f"\n{'指标':30s} {'与On-Off相关性':>12s} {'方向':>6s} {'解读':>20s}")
print("-" * 75)

corrs = {}
for col, label in features.items():
    r = df[col].corr(df[target])
    corrs[col] = r
    direction = "正向" if r > 0 else "负向"
    strength = "强" if abs(r) > 0.5 else ("中等" if abs(r) > 0.3 else "弱")
    bar = "#" * int(abs(r) * 30)
    print(f"  {label:28s}  {r:+.3f}      {direction}    {strength:>4s}  {bar}")

print(f"\n关键发现:")
best = max(corrs, key=lambda k: abs(corrs[k]))
worst = min(corrs, key=lambda k: abs(corrs[k]))
print(f"  最能预测赢球: {features[best]} (r={corrs[best]:+.3f})")
print(f"  最不能预测赢球: {features[worst]} (r={corrs[worst]:+.3f})")

# ── 3. 多元回归: 哪些指标组合最能预测赢球 ──
print()
print("=" * 70)
print("STEP 2: REGRESSION — 多个指标同时预测赢球")
print("=" * 70)

# 用进攻指标预测 On-Off
X_cols = ["d_Points_Per100", "TS_pct", "rTSPct",
          "d_Points_Created_Per100", "o_dpm", "d_Assists_Per100"]
X = StandardScaler().fit_transform(df[X_cols])
y = df[target].values

# 普通线性回归
lr = LinearRegression().fit(X, y)
print("\n线性回归 (各指标对赢球的标准化贡献):")
coefs = pd.Series(lr.coef_, index=X_cols)
coefs_pct = (coefs.abs() / coefs.abs().sum() * 100).round(1)
for col in X_cols:
    label = features.get(col, col)
    bar = "#" * int(coefs_pct[col] / 2)
    print(f"  {label:28s}: {coefs[col]:+.3f}  ({coefs_pct[col]:5.1f}%)  {bar}")
print(f"  R² = {lr.score(X, y):.4f}")

# Ridge 回归 (处理共线性)
ridge = Ridge(alpha=5.0).fit(X, y)
print("\nRidge回归 (抗共线性版本):")
r_coefs = pd.Series(ridge.coef_, index=X_cols)
r_pct = (r_coefs.abs() / r_coefs.abs().sum() * 100).round(1)
for col in X_cols:
    label = features.get(col, col)
    bar = "#" * int(r_pct[col] / 2)
    print(f"  {label:28s}: {r_coefs[col]:+.3f}  ({r_pct[col]:5.1f}%)  {bar}")
print(f"  R² = {ridge.score(X, y):.4f}")

# Lasso (自动筛选特征)
lasso = Lasso(alpha=0.5).fit(X, y)
print("\nLasso回归 (自动筛选最重要特征):")
l_coefs = pd.Series(lasso.coef_, index=X_cols)
for col in X_cols:
    label = features.get(col, col)
    status = "保留" if abs(l_coefs[col]) > 0.01 else "淘汰"
    print(f"  {label:28s}: {l_coefs[col]:+.3f}  [{status}]")
print(f"  R² = {lasso.score(X, y):.4f}")

kept = [col for col in X_cols if abs(l_coefs[col]) > 0.01]
print(f"\nLasso认为真正重要的指标: {[features.get(c,c) for c in kept]}")

# ── 4. 交叉验证: 模型真的有预测力吗？ ──
print()
print("=" * 70)
print("STEP 3: CROSS-VALIDATION — 模型的真实预测能力")
print("=" * 70)

loo = LeaveOneOut()
y_pred_cv = np.zeros(len(y))

for train_idx, test_idx in loo.split(X):
    ridge_cv = Ridge(alpha=5.0)
    ridge_cv.fit(X[train_idx], y[train_idx])
    y_pred_cv[test_idx] = ridge_cv.predict(X[test_idx])

cv_r2 = r2_score(y, y_pred_cv)
cv_mae = mean_absolute_error(y, y_pred_cv)

print(f"\nLeave-One-Out 交叉验证结果:")
print(f"  训练R² = {ridge.score(X, y):.4f} (模型在训练数据上的拟合)")
print(f"  测试R² = {cv_r2:.4f} (模型在未见数据上的预测力)")
print(f"  MAE = {cv_mae:.2f} (平均预测误差: ±{cv_mae:.1f}分)")

if cv_r2 > 0.3:
    print(f"\n  结论: 模型有真实预测力 (不是过拟合)")
else:
    print(f"\n  结论: 预测力有限，可能特征还不够")

# ── 5. 用赢球导向的权重重新排名 ──
print()
print("=" * 70)
print("STEP 4: OUTCOME-DRIVEN RANKING")
print("用'真正转化为赢球'的权重排名")
print("=" * 70)

# 用 Ridge 学到的权重 (这些权重代表"对赢球的真实贡献")
print("\n数据驱动的权重 (由On-Off目标学出):")
final_weights = r_coefs.abs() / r_coefs.abs().sum()
for col in X_cols:
    label = features.get(col, col)
    print(f"  {label:28s}: {final_weights[col]:.3f}")

# 对每个球员的巅峰5赛季计算排名
print("\n--- 巅峰5赛季排名 (用赢球导向权重) ---")
peak_rows = []
for player in df["player_name"].unique():
    pdf = df[df["player_name"] == player].nlargest(5, "o_dpm")
    row = {"player": player}
    row["years"] = f"{pdf['year'].min()}-{pdf['year'].max()}"
    row["n_seasons"] = len(pdf)
    for col in X_cols:
        row[col] = pdf[col].mean()
    row["actual_OnOff"] = pdf[target].mean()
    peak_rows.append(row)

peak = pd.DataFrame(peak_rows)
X_peak = StandardScaler().fit_transform(peak[X_cols])
peak["predicted_impact"] = Ridge(alpha=5.0).fit(X, y).predict(X_peak)
peak["rank"] = peak["predicted_impact"].rank(ascending=False).astype(int)
peak = peak.sort_values("rank")

print(f"\n{'Rank':>4s}  {'球员':18s}  {'巅峰期':>10s}  {'预测赢球贡献':>12s}  {'实际On-Off':>10s}  {'差距':>6s}")
print("-" * 70)
for _, r in peak.iterrows():
    gap = r["actual_OnOff"] - r["predicted_impact"]
    flag = ">" if gap > 2 else ("<" if gap < -2 else "=")
    print(f"  #{r['rank']:<3d} {r['player']:18s}  {r['years']:>10s}  "
          f"{r['predicted_impact']:>+10.2f}    {r['actual_OnOff']:>+8.2f}    {flag}{abs(gap):.1f}")

print("""
解读:
  预测赢球贡献: 模型根据各项数据预测这个球员应该对赢球贡献多少
  实际On-Off:   球员真实的在场/不在场效率差
  差距:
    > = 实际表现超出数据预测 → "隐藏价值" (如引力、领导力)
    < = 实际表现低于数据预测 → "数据虚高" (如空砍)
    = = 数据和表现匹配
""")

# ── 6. 全生涯排名 ──
print("=" * 70)
print("STEP 5: CAREER OUTCOME-DRIVEN RANKING")
print("=" * 70)

career_rows = []
for player in df["player_name"].unique():
    pdf = df[df["player_name"] == player]
    row = {"player": player, "seasons": len(pdf)}
    for col in X_cols:
        row[col] = pdf[col].mean()
    row["career_OnOff"] = pdf[target].mean()
    # 加权: 出场时间越多的赛季权重越大
    row["weighted_OnOff"] = np.average(pdf[target], weights=pdf["Minutes"])
    career_rows.append(row)

career = pd.DataFrame(career_rows)
X_career = StandardScaler().fit_transform(career[X_cols])
career["predicted"] = Ridge(alpha=5.0).fit(X, y).predict(X_career)
career["rank"] = career["weighted_OnOff"].rank(ascending=False).astype(int)
career = career.sort_values("rank")

print(f"\n{'Rank':>4s}  {'球员':18s}  {'赛季数':>5s}  {'加权On-Off':>10s}  {'模型预测':>8s}  {'差值':>6s}")
print("-" * 65)
for _, r in career.iterrows():
    gap = r["weighted_OnOff"] - r["predicted"]
    print(f"  #{r['rank']:<3d} {r['player']:18s}  {r['seasons']:>5.0f}  "
          f"{r['weighted_OnOff']:>+10.2f}  {r['predicted']:>+8.2f}  {gap:>+6.2f}")

# ── 7. 最终总结 ──
print()
print("=" * 70)
print("CONCLUSION: 数据到赢球的转化效率")
print("=" * 70)

print("""
核心发现:

1. 什么数据最能转化为赢球？
   → 模型权重告诉我们真正重要的是什么

2. 谁的数据"虚高"？(高数据但低赢球贡献)
   → 实际On-Off 远低于 模型预测

3. 谁有"隐藏价值"？(数据之外的赢球能力)
   → 实际On-Off 远高于 模型预测 (引力效应、领导力等)

4. 最终排名依据:
   → 不是谁数据好看
   → 而是谁真正让球队赢更多球
""")

# 保存
peak.to_csv("results/outcome_driven_ranking.csv", index=False)
career.to_csv("results/outcome_driven_career.csv", index=False)
print("-> Saved to results/outcome_driven_ranking.csv")
print("-> Saved to results/outcome_driven_career.csv")
