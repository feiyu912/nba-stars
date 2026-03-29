"""
Final Scoring Impact Model - 三数据源合并
==========================================
数据源:
  1. databallr API (2001-2026): O-DPM, On-Off, PtsCreated, rTS%
  2. stat-nba.com (1951-2020): PER, WS/48, USG%, 常规赛+季后赛
  3. NBA API (stats.nba.com): PPG, TS%, GP (全生涯)

方法: 标准化加权 + 季后赛加成 + Pace修正
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# ── 1. 加载三个数据源 ──
statnba_reg = pd.read_csv("data/statnba_regular_targets.csv")
statnba_po = pd.read_csv("data/statnba_playoffs_targets.csv")
nba_api = pd.read_csv("data/nba_career_stats_real.csv")
databallr = pd.read_csv("data/databallr_raw.csv")

# databallr: 合并 Luka 名字
databallr["player_name"] = databallr["player_name"].replace("Luka Dončić", "Luka Doncic")

print("=" * 70)
print("DATA SOURCES LOADED")
print("=" * 70)
print(f"  stat-nba regular: {len(statnba_reg)} players")
print(f"  stat-nba playoffs: {len(statnba_po)} players")
print(f"  NBA API: {nba_api['player'].nunique()} players, {len(nba_api)} seasons")
print(f"  databallr: {databallr['player_name'].nunique()} players, {len(databallr)} seasons")
print()

# ── 2. 从 NBA API 计算生涯真实 TS% ──
nba_career = nba_api.groupby("player").agg({
    "PPG": "mean",
    "TS_pct": "mean",
    "APG": "mean",
    "GP": "sum",
}).round(4).reset_index()

# ── 3. 从 databallr 计算巅峰期 (Top 5 by o_dpm) ──
peak_rows = []
for player in databallr["player_name"].unique():
    pdf = databallr[databallr["player_name"] == player].nlargest(5, "o_dpm")
    peak_rows.append({
        "player_en": player,
        "db_peak_years": f"{pdf['year'].min()}-{pdf['year'].max()}",
        "db_PPG": pdf["d_Points_PerGame"].mean(),
        "db_P100": pdf["d_Points_Per100"].mean(),
        "db_rTS": pdf["rTSPct"].mean(),
        "db_PtsCreated": pdf["d_Points_Created_PerGame"].mean(),
        "db_O_DPM": pdf["o_dpm"].mean(),
        "db_DPM": pdf["dpm"].mean(),
        "db_OnOff": pdf["netrtg_on_off"].mean(),
    })
db_peak = pd.DataFrame(peak_rows).round(3)

# ── 4. 合并所有数据 ──
df = statnba_reg[["player_en", "GP", "MPG", "PPG", "RPG", "APG",
                   "PER_base", "WS48", "USG", "OWS", "DWS", "WS"]].copy()
df = df.rename(columns={"PER_base": "PER"})

# 加入季后赛数据
po_cols = {"player_en": "player_en", "GP": "PO_GP", "PPG": "PO_PPG",
           "PER_base": "PO_PER", "WS48": "PO_WS48"}
if not statnba_po.empty:
    po = statnba_po[list(po_cols.keys())].rename(columns=po_cols)
    df = df.merge(po, on="player_en", how="left")

# 加入 NBA API 的 TS%
ts_map = dict(zip(nba_career["player"], nba_career["TS_pct"]))
df["TS_pct"] = df["player_en"].map(ts_map)

# 加入 databallr 巅峰数据
df = df.merge(db_peak, on="player_en", how="left")

# ── 5. Pace 修正 ──
era_map = {
    "Michael Jordan": "1990s", "LeBron James": "2010s",
    "Stephen Curry": "2010s", "Kevin Durant": "2010s",
    "Shaquille O'Neal": "2000s", "Kareem Abdul-Jabbar": "1970s",
    "Wilt Chamberlain": "1960s", "Kobe Bryant": "2000s",
    "James Harden": "2010s", "Luka Doncic": "2020s",
}
pace_map = {
    "1960s": 126, "1970s": 107, "1990s": 92,
    "2000s": 91, "2010s": 97, "2020s": 100,
}
league_ts_map = {
    "1960s": 0.490, "1970s": 0.510, "1990s": 0.535,
    "2000s": 0.530, "2010s": 0.555, "2020s": 0.572,
}

df["era"] = df["player_en"].map(era_map)
df["pace"] = df["era"].map(pace_map)
df["P100"] = (df["PPG"] * 100 / df["pace"]).round(2)
df["TS_plus"] = (df["TS_pct"] / df["era"].map(league_ts_map)).round(4)

# ── 6. 季后赛加成系数 ──
# 季后赛PER > 常规赛PER → 大场面球员加分
df["PO_boost"] = ((df["PO_PER"] - df["PER"]) / df["PER"] * 100).round(2)
df["PO_boost"] = df["PO_boost"].fillna(0)

print("=" * 70)
print("MERGED DATASET")
print("=" * 70)
show = ["player_en", "era", "GP", "PPG", "P100", "TS_pct", "TS_plus",
        "PER", "WS48", "USG", "PO_PER", "PO_boost"]
print(df[show].sort_values("PER", ascending=False).to_string(index=False))
print()

# ── 7. SCORING MODEL ──
# 分两层:
#   Layer 1: 所有 10 人都有的指标 (stat-nba + NBA API)
#   Layer 2: 2001+ 球员额外加 databallr 数据

print("=" * 70)
print("LAYER 1: Universal Scoring (all 10 players)")
print("=" * 70)

# 通用特征 (覆盖所有10人)
universal_features = ["P100", "TS_plus", "PER", "WS48"]
# 填充缺失值用列均值
for f in universal_features:
    df[f] = df[f].fillna(df[f].mean())

scaler = StandardScaler()
X_uni = scaler.fit_transform(df[universal_features])

# 权重:
#   P100:    0.30  得分产量 (Pace修正)
#   TS+:     0.20  相对效率
#   PER:     0.30  综合效率 (权威指标)
#   WS/48:   0.20  胜利贡献
w_uni = np.array([0.30, 0.20, 0.30, 0.20])
df["score_L1"] = X_uni @ w_uni

# 季后赛加成 (最多 +/-5%)
df["score_L1"] += df["PO_boost"] / 100 * 0.05 * df["score_L1"].abs().mean()

df["rank_L1"] = df["score_L1"].rank(ascending=False).astype(int)
result_L1 = df.sort_values("rank_L1")
print(result_L1[["rank_L1", "player_en", "era", "P100", "TS_plus", "PER",
                  "WS48", "PO_boost", "score_L1"]].round(3).to_string(index=False))
print()

# ── 8. LAYER 2: Modern Enhancement (2001+ players only) ──
print("=" * 70)
print("LAYER 2: Modern Enhancement (players with databallr data)")
print("=" * 70)

modern = df[df["db_O_DPM"].notna()].copy()
modern_features = ["P100", "TS_plus", "PER", "WS48", "db_O_DPM", "db_OnOff", "db_PtsCreated"]
X_mod = StandardScaler().fit_transform(modern[modern_features])

#   P100:        0.15
#   TS+:         0.10
#   PER:         0.15
#   WS/48:       0.10
#   O-DPM:       0.20  (最权威的现代进攻指标)
#   On-Off:      0.15  (实际场上影响)
#   PtsCreated:  0.15  (创造得分)
w_mod = np.array([0.15, 0.10, 0.15, 0.10, 0.20, 0.15, 0.15])
modern["score_L2"] = X_mod @ w_mod
modern["score_L2"] += modern["PO_boost"] / 100 * 0.05 * modern["score_L2"].abs().mean()
modern["rank_L2"] = modern["score_L2"].rank(ascending=False).astype(int)

print(modern.sort_values("rank_L2")[
    ["rank_L2", "player_en", "db_peak_years", "db_O_DPM", "db_OnOff",
     "db_PtsCreated", "PO_boost", "score_L2"]
].round(3).to_string(index=False))
print()

# ── 9. 最终对比 ──
print("=" * 70)
print("FINAL COMPARISON")
print("=" * 70)
final = df.sort_values("rank_L1")[["player_en", "rank_L1"]].copy()
mod_ranks = dict(zip(modern["player_en"], modern["rank_L2"]))
final["rank_L2"] = final["player_en"].map(mod_ranks)
final["rank_L2"] = final["rank_L2"].apply(lambda x: f"#{int(x)}" if pd.notna(x) else "N/A (pre-2001)")
print(final.to_string(index=False))

# ── 10. 保存 ──
df.sort_values("rank_L1").to_csv("results/final_scoring_ranking.csv", index=False)
print("\n-> Saved to results/final_scoring_ranking.csv")

# ── 11. 数据来源总结 ──
print()
print("=" * 70)
print("DATA SOURCES SUMMARY")
print("=" * 70)
print("""
Layer 1 (All 10 players):
  PPG, TS%:           NBA API (stats.nba.com)
  PER, WS/48, USG%:   stat-nba.com (历史生涯, 常规赛+季后赛)
  Pace estimates:      Basketball-Reference.com league averages

Layer 2 (8 modern players, 2001-2026):
  O-DPM, On-Off, PtsCreated, rTS%:  databallr.com API

Not included (pre-2001, no advanced data):
  Wilt Chamberlain:    Only Layer 1 metrics
  Kareem Abdul-Jabbar: Only Layer 1 metrics
""")
