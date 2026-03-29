"""
Phase 2: Era-Adjusted + Impact Model
=====================================
改进：
  1. PPG -> P100 (Pace修正): 消除时代节奏差异
  2. 加入 PER + WS/48 作为 On/Off 替代（综合影响力）
  3. Ridge回归思路：加入更多特征，观察排名稳定性
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ── 1. 读取数据 ──
df = pd.read_csv("data/players_peak.csv")

# ── 2. 特征工程 ──
# TS+: 相对效率
df["TS_plus"] = df["TS_pct"] / df["league_TS"]

# Pace 修正：用 era-specific pace 估算 P100
# 历史 Pace 估算（每48分钟回合数）
pace_by_era = {
    "1960s": 126.0,  # 张伯伦时代，极快
    "1970s": 107.0,  # 贾巴尔时代
    "1990s": 92.0,   # 乔丹时代，最慢
    "2000s": 91.0,   # 科比/奥尼尔时代
    "2010s": 97.0,   # 詹姆斯/库里/杜兰特/哈登
    "2020s": 100.0,  # 东契奇时代
}
reference_pace = 100.0  # 以100回合为基准

df["pace"] = df["era"].map(pace_by_era)
df["P100"] = df["PPG"] * (reference_pace / df["pace"])

print("=" * 60)
print("Pace 修正效果 (PPG -> P100)")
print("=" * 60)
print(df[["player", "era", "PPG", "pace", "P100"]].round(2).to_string(index=False))
print()

# ── 3. 特征选择 ──
features = ["P100", "TS_plus", "AST_pct", "PER", "WS_per48"]

print("=" * 60)
print("相关性矩阵 (5 features)")
print("=" * 60)
print(df[features].corr().round(3))
print()

# ── 4. 标准化 ──
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[features])

# ── 5. 加权评分 ──
# 权重设计：
#   P100     0.30 → 得分能力（已Pace修正）
#   TS+      0.25 → 效率
#   AST%     0.10 → 组织（降低，避免哈登/东契奇虚高）
#   PER      0.20 → 综合进攻效率（替代On/Off）
#   WS/48    0.15 → 胜利贡献（实际影响力）
weights = np.array([0.30, 0.25, 0.10, 0.20, 0.15])
df["Score"] = X_scaled @ weights

# ── 6. 排名 ──
df["Rank"] = df["Score"].rank(ascending=False).astype(int)
df = df.sort_values("Rank")

# ── 7. 输出 ──
print("=" * 60)
print("Phase 2 Era-Adjusted Ranking")
print("=" * 60)
cols = ["Rank", "player", "era", "P100", "TS_plus", "PER", "WS_per48", "Score"]
result = df[cols].copy()
result["P100"] = result["P100"].round(1)
result["TS_plus"] = result["TS_plus"].round(3)
result["Score"] = result["Score"].round(4)
print(result.to_string(index=False))

# ── 8. Sanity Check ──
print()
print("=" * 60)
print("Sanity Check")
print("=" * 60)
top4 = set(df.nsmallest(4, "Rank")["player"])
expected_top = {"Michael Jordan", "LeBron James", "Stephen Curry", "Kevin Durant"}
overlap = top4 & expected_top
print(f"前4名中命中预期球员: {len(overlap)}/4 -> {overlap}")
if len(overlap) >= 3:
    print("[PASS] 排名基本合理")
else:
    print("[WARN] 需要进一步调整")

# ── 9. 与 Phase 1 对比 ──
print()
print("=" * 60)
print("vs Phase 1 关键变化")
print("=" * 60)
v1 = pd.read_csv("results/ranking_v1.csv")
v1_rank = dict(zip(v1["player"], v1["Rank"]))
for _, row in df.iterrows():
    p = row["player"]
    old = v1_rank.get(p, "?")
    new = row["Rank"]
    delta = old - new
    arrow = "^" if delta > 0 else ("v" if delta < 0 else "=")
    print(f"  {p:25s}  #{old} -> #{new}  ({arrow}{abs(delta)})")

# ── 10. 保存 ──
output = df[["Rank", "player", "era", "P100", "TS_plus", "AST_pct", "PER", "WS_per48", "Score"]]
output.to_csv("results/ranking_v2.csv", index=False)
print()
print("-> 结果已保存至 results/ranking_v2.csv")
