"""
两张独立排名表 (含季后赛加权)
================================
表1: 得分能力 — 进球多 + 效率高 + 大赛表现
表2: 进攻影响力 — 对球队进攻的整体贡献

得分能力:
  常规赛得分指数 × 0.5 + 季后赛得分指数 × 0.5
  季后赛权重和常规赛相同，但季后赛没打过/打得少的球员自然下降

  A = PPG(罚球7折) × TS+
  C = PPG/MIN(罚球7折) × TS+ × 竞争强度
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import warnings
warnings.filterwarnings('ignore')

# ── 加载 ──
reg = pd.read_csv("data/nba100_career_all.csv")  # 常规赛
po = pd.read_csv("data/nba100_playoffs.csv")       # 季后赛
db = pd.read_csv("data/nba100_databallr.csv")
db["player_name"] = db["player_name"].replace({
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
})

# ── 统一处理函数 ──
PACE, LTS, TEAMS = {}, {}, {}
for y in range(1955, 1965): PACE[y], LTS[y], TEAMS[y] = 125, 0.460, 9
for y in range(1965, 1975): PACE[y], LTS[y], TEAMS[y] = 110, 0.490, 15
for y in range(1975, 1985): PACE[y], LTS[y], TEAMS[y] = 103, 0.520, 23
for y in range(1985, 1995): PACE[y], LTS[y], TEAMS[y] = 95, 0.535, 26
for y in range(1995, 2005): PACE[y], LTS[y], TEAMS[y] = 91, 0.530, 29
for y in range(2005, 2015): PACE[y], LTS[y], TEAMS[y] = 95, 0.545, 30
for y in range(2015, 2026): PACE[y], LTS[y], TEAMS[y] = 100, 0.570, 30

def process_data(df):
    """计算得分指数 (常规赛和季后赛通用)"""
    df = df.copy()
    df["year"] = df["season"].str[:4].astype(int)
    df["TS_pct"] = df["PPG"] / (2 * (df["FGA"] + 0.44 * df["FTA"]))
    df["PPM"] = df["PPG"] / df["MIN"].replace(0, 1)
    df["FT_points"] = df["FTM"] * 1.0
    df["FG_points"] = df["PPG"] - df["FT_points"]
    df["PPG_adj_ft"] = df["FG_points"] + df["FT_points"] * 0.7
    df["PPM_adj_ft"] = df["PPG_adj_ft"] / df["MIN"].replace(0, 1)
    df["pace"] = df["year"].map(PACE).fillna(97)
    df["lts"] = df["year"].map(LTS).fillna(0.545)
    df["teams"] = df["year"].map(TEAMS).fillna(30)
    df["competition"] = (df["teams"] / 30).pow(0.5)
    df["PPG_adj"] = df["PPG_adj_ft"] * (97 / df["pace"])
    df["TS_plus"] = df["TS_pct"] / df["lts"]

    # 得分稀缺性: 你的PPG相对于同年所有球员有多突出
    # 在低得分年代(90s-00s)得高分 → 更大的Z-score → 更高的奖励
    year_stats = df.groupby("year")["PPG"].agg(["mean", "std"]).reset_index()
    year_stats.columns = ["year", "year_ppg_mean", "year_ppg_std"]
    df = df.merge(year_stats, on="year", how="left")
    df["year_ppg_std"] = df["year_ppg_std"].replace(0, 1)
    df["ppg_zscore"] = (df["PPG"] - df["year_ppg_mean"]) / df["year_ppg_std"]
    # 将Z-score转化为乘数: Z=0→1.0, Z=1→1.1, Z=2→1.2 (温和加成)
    df["scarcity"] = 1 + df["ppg_zscore"] * 0.1

    # A: 每场高效得分 × 稀缺性
    df["scoreA"] = df["PPG_adj"] * df["TS_plus"] * df["scarcity"]
    # C: 时代修正每分钟 × 稀缺性
    df["scoreC"] = df["PPM_adj_ft"] * df["TS_plus"] * df["competition"] * df["scarcity"]
    return df

def summarize(df, prefix):
    """生涯平均 + 巅峰5年"""
    career_a = df.groupby("player")["scoreA"].mean().round(3).reset_index()
    career_a.columns = ["player", f"{prefix}_A_career"]
    peak_a = df.groupby("player")["scoreA"].apply(
        lambda x: x.nlargest(5).mean()).round(3).reset_index()
    peak_a.columns = ["player", f"{prefix}_A_peak"]

    career_c = df.groupby("player")["scoreC"].mean().round(4).reset_index()
    career_c.columns = ["player", f"{prefix}_C_career"]
    peak_c = df.groupby("player")["scoreC"].apply(
        lambda x: x.nlargest(5).mean()).round(4).reset_index()
    peak_c.columns = ["player", f"{prefix}_C_peak"]

    stats = df.groupby("player").agg({
        "PPG": "mean", "TS_pct": "mean", "GP": "sum",
        "APG": "mean", "FTM": "mean", "MIN": "mean",
    }).round(3).reset_index()
    stats.columns = ["player", f"{prefix}_PPG", f"{prefix}_TS",
                      f"{prefix}_GP", f"{prefix}_APG", f"{prefix}_FTM",
                      f"{prefix}_MPG"]

    result = stats.merge(career_a, on="player").merge(peak_a, on="player")
    result = result.merge(career_c, on="player").merge(peak_c, on="player")
    return result

# ── 处理常规赛和季后赛 ──
reg = process_data(reg)
po = process_data(po)

reg_sum = summarize(reg, "reg")
po_sum = summarize(po, "po")

# 合并
career = reg_sum.merge(po_sum, on="player", how="left")

# 季后赛场次缺失的填0
for col in career.columns:
    if col.startswith("po_") and col != "player":
        career[col] = career[col].fillna(0)

# ── 加权得分指数 ──
# 每场季后赛 = 3倍常规赛含金量 (季后赛对手更强、压力更大、防守更紧)
# 权重自动算出:
#   季后赛权重 = (季后赛场次 × 3) / (常规赛场次 + 季后赛场次 × 3)
#   乔丹: 1072 + 179×3=537 → 季后赛占33%
#   没打过季后赛的: 0%
PLAYOFF_MULTIPLIER = 3
career["po_weighted_gp"] = career["po_GP"] * PLAYOFF_MULTIPLIER
career["total_weighted_gp"] = career["reg_GP"] + career["po_weighted_gp"]
career["po_weight"] = career["po_weighted_gp"] / career["total_weighted_gp"]
career["reg_weight"] = 1 - career["po_weight"]

for view in ["A", "C"]:
    # 巅峰 vs 生涯: 固定60/40 (巅峰至少要占多数, 这比较合理)
    career[f"reg_{view}"] = 0.6 * career[f"reg_{view}_peak"] + 0.4 * career[f"reg_{view}_career"]
    career[f"po_{view}"] = 0.6 * career[f"po_{view}_peak"] + 0.4 * career[f"po_{view}_career"]
    # 常规赛/季后赛按实际场次比例
    career[f"total_{view}"] = career["reg_weight"] * career[f"reg_{view}"] + \
                               career["po_weight"] * career[f"po_{view}"]
    career[f"total_{view}_rank"] = career[f"total_{view}"].rank(ascending=False).astype(int)

# 最终得分排名 = A和C的中位数
career["scoring_median"] = career[["total_A_rank", "total_C_rank"]].median(axis=1)
career["scoring_rank"] = career["scoring_median"].rank().astype(int)

# ── 表2: 进攻影响力 ──
# 用常规赛基础数据预测O-DPM (和之前一样)
reg_career = reg.groupby("player").agg({
    "PPG": "mean", "TS_pct": "mean", "APG": "mean",
    "FGA": "mean", "MIN": "mean",
}).round(4).reset_index()
# FTR and TOV
ftr = reg.groupby("player")["FTM"].mean() / reg.groupby("player")["FGA"].mean()
career["FTR"] = career["player"].map(dict(zip(ftr.index, ftr))).fillna(ftr.median())
tov = reg.groupby("player").apply(lambda x: x["PPG"].mean() * 0 if "TOV" not in x.columns else 0).fillna(0)

peak_ppg = reg.groupby("player")["PPG"].apply(
    lambda x: x.nlargest(5).mean()).round(2)
career["peak_PPG"] = career["player"].map(dict(zip(peak_ppg.index, peak_ppg)))
career["TOV"] = 0  # placeholder, TOV not in playoff data columns

db_c = db.groupby("player_name").agg({"o_dpm": "mean"}).round(3).reset_index()
db_c.columns = ["player", "o_dpm"]
career = career.merge(db_c, on="player", how="left")

features = ["reg_PPG", "reg_TS", "reg_APG", "peak_PPG"]
train_mask = career["o_dpm"].notna()
for f in features:
    career[f] = career[f].fillna(career[f].median())

scaler = StandardScaler()
X_all = scaler.fit_transform(career[features])
X_tr = X_all[train_mask.values]
ridge = Ridge(alpha=2.0).fit(X_tr, career.loc[train_mask, "o_dpm"].values)
career["impact_score"] = ridge.predict(X_all)
career["impact_rank"] = career["impact_score"].rank(ascending=False).astype(int)

# ── 罚球占比 ──
career["FT_pct_scoring"] = (career["reg_FTM"] / career["reg_PPG"] * 100).round(1)

# ── 输出表1 ──
career = career.sort_values("scoring_rank")

print("=" * 95)
print("表1: 得分能力排名 (常规赛50% + 季后赛50%)")
print("=" * 95)
print("""
方法:
  A = PPG(罚球7折, pace修正) × TS+
  C = PPG/MIN(罚球7折) × TS+ × 竞争强度
  每场季后赛 = 3倍常规赛含金量
  常规赛/季后赛权重按加权场次自动算:
    乔丹: 1072 + 179×3 → 季后赛占33%
    恩比德: 487 + 59×3 → 季后赛占27% (但季后赛得分低→拉分)
  最终 = A和C取中位数
""")

print(f"{'Rk':>3s}  {'Player':28s} {'A':>3s} {'C':>3s}  "
      f"{'regPPG':>6s} {'poPPG':>6s} {'poGP':>4s} {'FT%s':>4s}")
print("-" * 78)
for _, r in career.iterrows():
    po_ppg = f"{r['po_PPG']:5.1f}" if r['po_GP'] > 0 else "  N/A"
    print(f" {int(r['scoring_rank']):3d}  {r['player']:28s} "
          f"{int(r['total_A_rank']):3d} {int(r['total_C_rank']):3d}  "
          f"{r['reg_PPG']:5.1f}  {po_ppg} {int(r['po_GP']):4d} "
          f"{r['FT_pct_scoring']:4.1f}%")

# ── 输出表2 ──
print()
print("=" * 95)
print("表2: 进攻影响力排名")
print("=" * 95)

impact = career.sort_values("impact_rank")
print(f"\n{'Rk':>3s}  {'Player':28s} {'Pred':>6s} {'Actual':>7s}  "
      f"{'PPG':>5s} {'APG':>4s}")
print("-" * 60)
for _, r in impact.head(30).iterrows():
    actual = f"{r['o_dpm']:+5.2f}*" if pd.notna(r["o_dpm"]) else "    - "
    print(f" {int(r['impact_rank']):3d}  {r['player']:28s} "
          f"{r['impact_score']:+5.2f}  {actual}  "
          f"{r['reg_PPG']:5.1f} {r['reg_APG']:4.1f}")

# ── 两表对比 ──
print()
print("=" * 95)
print("两表对比 TOP 30")
print("=" * 95)

compare = career[["player", "scoring_rank", "impact_rank"]].copy()
compare["diff"] = compare["impact_rank"] - compare["scoring_rank"]
compare = compare.sort_values("scoring_rank")

print(f"  {'Player':28s} {'得分':>4s} {'影响力':>6s} {'差值':>5s}  {'类型'}")
print("-" * 65)
for _, r in compare.head(30).iterrows():
    d = int(r["diff"])
    if d < -10: ptype = "组织型"
    elif d > 10: ptype = "纯得分手"
    else: ptype = "均衡"
    print(f"  {r['player']:28s} #{int(r['scoring_rank']):3d}  #{int(r['impact_rank']):3d}  "
          f"{d:+4d}   {ptype}")

# 保存
out_scoring = career.sort_values("scoring_rank")[
    ["scoring_rank", "player", "reg_PPG", "po_PPG", "reg_TS", "po_TS",
     "reg_GP", "po_GP", "FT_pct_scoring",
     "total_A_rank", "total_C_rank"]
]
out_scoring.to_csv("results/scoring_ranking.csv", index=False)

out_impact = career.sort_values("impact_rank")[
    ["impact_rank", "player", "reg_PPG", "reg_APG", "reg_TS",
     "impact_score", "o_dpm"]
]
out_impact.to_csv("results/impact_ranking.csv", index=False)
print(f"\n-> results/scoring_ranking.csv")
print(f"-> results/impact_ranking.csv")

# ══════════════════════════════════════════
# 改进1: 敏感性分析 (罚球惩罚 0.6/0.7/0.8)
# ══════════════════════════════════════════
print()
print("=" * 95)
print("SENSITIVITY ANALYSIS: 罚球惩罚系数 0.6 / 0.7 / 0.8")
print("=" * 95)
print("如果排名在不同系数下变化很小 → 结果稳健; 变化大 → 对该参数敏感")

def calc_scoring_rank(nba_df, ft_discount):
    """用不同罚球折扣重算得分排名"""
    d = nba_df.copy()
    d["FT_pts"] = d["FTM"] * 1.0
    d["FG_pts"] = d["PPG"] - d["FT_pts"]
    d["PPG_ft"] = d["FG_pts"] + d["FT_pts"] * ft_discount
    d["PPG_adj"] = d["PPG_ft"] * (97 / d["pace"])
    d["PPM_ft"] = d["PPG_ft"] / d["MIN"].replace(0, 1)
    d["sA"] = d["PPG_adj"] * d["TS_plus"]
    d["sC"] = d["PPM_ft"] * d["TS_plus"] * d["competition"]
    # 按常规赛/季后赛分开汇总再合并 (简化: 用全部数据)
    a = d.groupby("player")["sA"].apply(lambda x: 0.6*x.nlargest(5).mean() + 0.4*x.mean())
    c = d.groupby("player")["sC"].apply(lambda x: 0.6*x.nlargest(5).mean() + 0.4*x.mean())
    ranks_a = a.rank(ascending=False).astype(int)
    ranks_c = c.rank(ascending=False).astype(int)
    median_r = pd.DataFrame({"A": ranks_a, "C": ranks_c}).median(axis=1)
    return median_r.rank().astype(int)

# 合并常规赛+季后赛数据用于敏感性分析
all_games = pd.concat([reg, po], ignore_index=True)

ranks_06 = calc_scoring_rank(all_games, 0.6)
ranks_07 = calc_scoring_rank(all_games, 0.7)
ranks_08 = calc_scoring_rank(all_games, 0.8)

sens = pd.DataFrame({
    "player": ranks_07.index,
    "FT=0.6": ranks_06.values,
    "FT=0.7": ranks_07.values,
    "FT=0.8": ranks_08.values,
})
sens["range"] = sens[["FT=0.6", "FT=0.7", "FT=0.8"]].max(axis=1) - \
                sens[["FT=0.6", "FT=0.7", "FT=0.8"]].min(axis=1)
sens = sens.sort_values("FT=0.7")

print(f"\n{'Player':28s} {'FT=0.6':>6s} {'FT=0.7':>6s} {'FT=0.8':>6s} {'波动':>4s}  {'判定'}")
print("-" * 65)
for _, r in sens.head(30).iterrows():
    stability = "稳定" if r["range"] <= 2 else ("轻微" if r["range"] <= 5 else "敏感")
    print(f"  {r['player']:28s} #{int(r['FT=0.6']):3d}  #{int(r['FT=0.7']):3d}  "
          f"#{int(r['FT=0.8']):3d}   {int(r['range']):2d}   {stability}")

print(f"\n最敏感的球员 (罚球系数对排名影响最大):")
for _, r in sens.nlargest(10, "range").iterrows():
    print(f"  {r['player']:28s}  波动{int(r['range'])}位  "
          f"(FT占比高, 系数变化影响大)")

# ══════════════════════════════════════════
# 改进2: 现代 vs 历史对比
# ══════════════════════════════════════════
print()
print("=" * 95)
print("MODERN vs HISTORICAL: 分时代对比")
print("=" * 95)

def get_era(player):
    r = career[career["player"] == player]
    if len(r) == 0: return "Unknown"
    # 简单用数据源判断
    has_db = pd.notna(r.iloc[0].get("o_dpm"))
    return "Modern (2001+)" if has_db else "Historical (pre-2001)"

career["era_group"] = career["player"].apply(get_era)

for era in ["Modern (2001+)", "Historical (pre-2001)"]:
    era_players = career[career["era_group"] == era].sort_values("scoring_rank")
    print(f"\n--- {era} (TOP 15) ---")
    for i, (_, r) in enumerate(era_players.head(15).iterrows()):
        print(f"  #{int(r['scoring_rank']):3d}  {r['player']:28s}  PPG={r['reg_PPG']:5.1f}")

# ══════════════════════════════════════════
# 改进3: 解释层 — 每个球员为什么排在这
# ══════════════════════════════════════════
print()
print("=" * 95)
print("EXPLANATION: TOP 20 球员排名解释")
print("=" * 95)

# 计算标准化指标用于解释
from sklearn.preprocessing import StandardScaler
explain_cols = ["reg_PPG", "reg_TS", "po_PPG", "po_GP", "FT_pct_scoring"]
explain_data = career[explain_cols].copy()
explain_data["po_PPG"] = explain_data["po_PPG"].fillna(0)

scaler_e = StandardScaler()
z_scores = pd.DataFrame(
    scaler_e.fit_transform(explain_data),
    columns=[f"{c}_z" for c in explain_cols],
    index=career.index
)

career = pd.concat([career, z_scores], axis=1)

print()
top20 = career.sort_values("scoring_rank").head(20)
for _, r in top20.iterrows():
    print(f"#{int(r['scoring_rank']):3d} {r['player']}")
    factors = []
    if r["reg_PPG_z"] > 1.0: factors.append(f"  + 常规赛高产 (PPG={r['reg_PPG']:.1f}, +{r['reg_PPG_z']:.1f}σ)")
    elif r["reg_PPG_z"] > 0: factors.append(f"  + 常规赛得分中上 (PPG={r['reg_PPG']:.1f}, +{r['reg_PPG_z']:.1f}σ)")
    else: factors.append(f"  - 常规赛得分偏低 (PPG={r['reg_PPG']:.1f}, {r['reg_PPG_z']:.1f}σ)")

    if r["reg_TS_z"] > 0.5: factors.append(f"  + 效率出色 (TS={r['reg_TS']:.3f}, +{r['reg_TS_z']:.1f}σ)")
    elif r["reg_TS_z"] < -0.5: factors.append(f"  - 效率偏低 (TS={r['reg_TS']:.3f}, {r['reg_TS_z']:.1f}σ)")

    if r["po_GP"] > 100:
        if r["po_PPG"] > r["reg_PPG"]:
            factors.append(f"  + 季后赛更强 ({r['po_PPG']:.1f} > {r['reg_PPG']:.1f}, {int(r['po_GP'])}场)")
        else:
            factors.append(f"  ~ 季后赛略降 ({r['po_PPG']:.1f} < {r['reg_PPG']:.1f}, {int(r['po_GP'])}场)")
    elif r["po_GP"] > 0:
        factors.append(f"  ~ 季后赛经验有限 ({int(r['po_GP'])}场)")
    else:
        factors.append(f"  - 无季后赛数据")

    if r["FT_pct_scoring"] > 28:
        factors.append(f"  - 罚球占比高 ({r['FT_pct_scoring']:.1f}%, 被惩罚)")
    elif r["FT_pct_scoring"] < 18:
        factors.append(f"  + 罚球占比低 ({r['FT_pct_scoring']:.1f}%, 投篮为主)")

    for f in factors:
        print(f)
    print()

# 保存完整数据
career.sort_values("scoring_rank").to_csv("results/scoring_ranking.csv", index=False)
career.sort_values("impact_rank").to_csv("results/impact_ranking.csv", index=False)
print("-> results updated")
