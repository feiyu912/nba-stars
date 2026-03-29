"""
Offense in Defensive Context
==============================
核心观点: 脱离防守谈进攻是无意义的

1. 面对强防守还能高效得分 → 真正的进攻强
2. 自己也能防守 → 不会在防守端把进攻赚的吐回去
3. 完整的进攻评价 = 进攻产出 - 防守端的代价

关键指标:
  O-DPM: 纯进攻影响力
  D-DPM: 防守影响力 (= DPM - O-DPM)
  DPM:   完整影响力 (进攻+防守)
  On-Off: 最终比赛结果 (包含一切)
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

df = pd.read_csv("data/databallr_raw.csv")
df["player_name"] = df["player_name"].replace("Luka Dončić", "Luka Doncic")

# 计算防守 DPM
df["d_dpm"] = df["dpm"] - df["o_dpm"]

# ═══════════════════════════════════════
# STEP 1: 进攻 vs 防守 — 谁在防守端"吐回去"了？
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 1: 进攻赚的 vs 防守亏的")
print("真正的进攻能力 = 进攻端赚的 - 防守端亏的")
print("=" * 70)

career = df.groupby("player_name").agg({
    "o_dpm": "mean",
    "d_dpm": "mean",
    "dpm": "mean",
    "netrtg_on_off": "mean",
    "d_Points_PerGame": "mean",
    "TS_pct": "mean",
    "rTSPct": "mean",
    "d_Points_Created_PerGame": "mean",
    "Minutes": "sum",
    "GamesPlayed": "sum",
    "year": "count",
}).rename(columns={"year": "seasons"}).round(3)

career = career.sort_values("dpm", ascending=False)

print(f"\n{'球员':18s} {'O-DPM':>6s} {'D-DPM':>6s} {'= DPM':>6s} {'On-Off':>7s} {'防守代价':>8s}")
print("-" * 60)
for player, r in career.iterrows():
    # 防守代价: D-DPM为负说明防守在拖后腿
    cost = "防守拖累" if r["d_dpm"] < -0.5 else ("攻防兼备" if r["d_dpm"] > 0.5 else "防守中性")
    print(f"  {player:16s}  {r['o_dpm']:+5.2f}  {r['d_dpm']:+5.2f}  {r['dpm']:+5.2f}  "
          f"{r['netrtg_on_off']:+6.2f}   {cost}")

print("""
解读:
  O-DPM高 + D-DPM正 = 攻防一体 (最强)
  O-DPM高 + D-DPM负 = 进攻强但防守拖后腿
  → DPM = O-DPM + D-DPM = 球员的"净贡献"
""")

# ═══════════════════════════════════════
# STEP 2: "有效进攻" = 考虑防守代价后的进攻价值
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 2: Effective Offense (考虑防守代价的进攻)")
print("=" * 70)

# 有效进攻 = O-DPM - max(0, -D-DPM * penalty_factor)
# 如果防守很差(D-DPM << 0)，要从进攻价值里扣分
# 如果防守好(D-DPM > 0)，给进攻加分（攻防一体奖励）
career["defense_tax"] = career["d_dpm"].apply(
    lambda x: x * 0.3 if x < 0 else x * 0.2  # 防守差扣30%, 防守好加20%
)
career["effective_offense"] = career["o_dpm"] + career["defense_tax"]
career["eff_rank"] = career["effective_offense"].rank(ascending=False).astype(int)

print(f"\n{'Rank':>4s}  {'球员':18s} {'O-DPM':>6s} {'防守税/奖':>8s} {'= 有效进攻':>10s} {'vs 纯进攻排名变化':>18s}")
print("-" * 72)

# 纯进攻排名
career["pure_o_rank"] = career["o_dpm"].rank(ascending=False).astype(int)

for _, r in career.sort_values("eff_rank").iterrows():
    delta = r["pure_o_rank"] - r["eff_rank"]
    arrow = f"^{int(delta)}" if delta > 0 else (f"v{int(-delta)}" if delta < 0 else "=")
    print(f"  #{int(r['eff_rank']):<3d} {_:16s}  {r['o_dpm']:+5.2f}  {r['defense_tax']:+7.3f}  "
          f"{r['effective_offense']:+9.3f}       纯进攻#{int(r['pure_o_rank'])} → #{int(r['eff_rank'])} ({arrow})")

# ═══════════════════════════════════════
# STEP 3: 逐赛季分析 — 进攻效率 vs 面对的防守压力
# ═══════════════════════════════════════
print()
print("=" * 70)
print("STEP 3: 巅峰赛季的攻防完整画像")
print("=" * 70)

peak_rows = []
for player in df["player_name"].unique():
    # 用 DPM (完整影响力) 选巅峰，不是只看进攻
    pdf = df[df["player_name"] == player].nlargest(5, "dpm")
    peak_rows.append({
        "player": player,
        "years": f"{pdf['year'].min()}-{pdf['year'].max()}",
        "PPG": pdf["d_Points_PerGame"].mean(),
        "rTS": pdf["rTSPct"].mean(),
        "PtsCreated": pdf["d_Points_Created_PerGame"].mean(),
        "O_DPM": pdf["o_dpm"].mean(),
        "D_DPM": pdf["d_dpm"].mean(),
        "DPM": pdf["dpm"].mean(),
        "OnOff": pdf["netrtg_on_off"].mean(),
    })

peak = pd.DataFrame(peak_rows).round(3)

print(f"\n{'球员':18s} {'PPG':>5s} {'rTS%':>5s} {'O-DPM':>6s} {'D-DPM':>6s} {'= DPM':>6s} {'On-Off':>7s}")
print("-" * 62)
for _, r in peak.sort_values("DPM", ascending=False).iterrows():
    print(f"  {r['player']:16s} {r['PPG']:5.1f} {r['rTS']:+5.1f}  "
          f"{r['O_DPM']:+5.2f}  {r['D_DPM']:+5.2f}  {r['DPM']:+5.2f}  {r['OnOff']:+6.2f}")

# ═══════════════════════════════════════
# STEP 4: 最终 — DPM才是真正的"完整进攻"排名
# ═══════════════════════════════════════
print()
print("=" * 70)
print("STEP 4: THREE RANKINGS COMPARISON")
print("纯进攻 vs 有效进攻 vs 完整影响力 vs 最终赢球")
print("=" * 70)

# 各种排名
career["onoff_rank"] = career["netrtg_on_off"].rank(ascending=False).astype(int)
career["dpm_rank"] = career["dpm"].rank(ascending=False).astype(int)

compare = career[["o_dpm", "pure_o_rank", "effective_offense", "eff_rank",
                    "dpm", "dpm_rank", "netrtg_on_off", "onoff_rank"]].copy()
compare.columns = ["O-DPM", "纯进攻", "有效进攻值", "有效进攻",
                     "DPM", "完整影响", "On-Off", "赢球结果"]

print(compare.sort_values("赢球结果").to_string())

print("""
解读:
  纯进攻排名:   只看进攻数据
  有效进攻排名: 考虑防守代价后的进攻
  完整影响排名: DPM (进攻+防守)
  赢球结果排名: On-Off (最终比赛结果)

如果一个球员从"纯进攻"到"赢球结果"排名上升 → 防守在帮他
如果排名下降 → 防守在拖他后腿
""")

# ═══════════════════════════════════════
# STEP 5: 量化"防守语境下的进攻效率"
# ═══════════════════════════════════════
print("=" * 70)
print("STEP 5: OFFENSIVE EFFICIENCY IN DEFENSIVE CONTEXT")
print("用回归量化: 防守端贡献对进攻评价的修正幅度")
print("=" * 70)

# 模型: On-Off = f(O-DPM, D-DPM) → 看两端各自贡献多少
X = StandardScaler().fit_transform(df[["o_dpm", "d_dpm"]])
y = df["netrtg_on_off"].values

ridge = Ridge(alpha=1.0).fit(X, y)
print(f"\n  On-Off = {ridge.coef_[0]:+.3f} * O-DPM + {ridge.coef_[1]:+.3f} * D-DPM + {ridge.intercept_:.3f}")
print(f"  R² = {ridge.score(X, y):.4f}")

o_pct = abs(ridge.coef_[0]) / (abs(ridge.coef_[0]) + abs(ridge.coef_[1])) * 100
d_pct = 100 - o_pct
print(f"\n  进攻端贡献: {o_pct:.1f}% of winning")
print(f"  防守端贡献: {d_pct:.1f}% of winning")
print(f"\n  → 赢球 = {o_pct:.0f}% 进攻 + {d_pct:.0f}% 防守")
print(f"  → 忽略防守等于忽略了 {d_pct:.0f}% 的比赛")

# ═══════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════
print()
print("=" * 70)
print("FINAL: 完整进攻能力评价 (含防守语境)")
print("=" * 70)

final = career[["o_dpm", "d_dpm", "dpm", "effective_offense",
                 "netrtg_on_off", "seasons"]].copy()
final["complete_score"] = (
    0.4 * StandardScaler().fit_transform(final[["effective_offense"]]).flatten() +
    0.3 * StandardScaler().fit_transform(final[["dpm"]]).flatten() +
    0.3 * StandardScaler().fit_transform(final[["netrtg_on_off"]]).flatten()
)
final["final_rank"] = final["complete_score"].rank(ascending=False).astype(int)

print(f"\n{'Rank':>4s}  {'球员':18s} {'O-DPM':>6s} {'D-DPM':>6s} {'有效进攻':>8s} {'DPM':>5s} {'On-Off':>7s} {'总分':>6s}")
print("-" * 70)
for player, r in final.sort_values("final_rank").iterrows():
    print(f"  #{int(r['final_rank']):<3d} {player:16s}  {r['o_dpm']:+5.2f}  {r['d_dpm']:+5.2f}  "
          f"{r['effective_offense']:+7.3f}  {r['dpm']:+4.2f}  {r['netrtg_on_off']:+6.2f}  {r['complete_score']:+5.3f}")

print("""
这才是完整的进攻评价:
  不是"谁得分最多"
  而是"谁对球队赢球的进攻贡献最大，同时不在防守端漏洞"
""")

final.to_csv("results/offense_in_context.csv")
print("-> Saved to results/offense_in_context.csv")
