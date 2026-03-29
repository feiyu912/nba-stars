"""
Final Model: 基于 databallr.com 真实高阶数据
=============================================
数据源: databallr API (2001-2026)
指标: Points, TS%, rTS%, PtsCreated, O-DPM, On-Off, Assists
覆盖: 8名球员 (张伯伦/贾巴尔 无数据，需单独处理)
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

# ── 1. 加载数据 ──
df = pd.read_csv("data/databallr_raw.csv")

# 合并 Luka Doncic / Luka Dončić
df["player_name"] = df["player_name"].replace("Luka Dončić", "Luka Doncic")

print("=" * 70)
print("RAW DATA SUMMARY (databallr API, 2001-2026)")
print("=" * 70)
print(f"Total player-seasons: {len(df)}")
print(f"Players: {sorted(df['player_name'].unique())}")
print(f"Columns: {list(df.columns)}")
print()

# ── 2. 每位球员的生涯平均 ──
career = df.groupby("player_name").agg({
    "d_Points_PerGame": "mean",
    "d_Points_Per100": "mean",
    "TS_pct": "mean",
    "rTSPct": "mean",
    "d_Points_Created_PerGame": "mean",
    "d_Points_Created_Per100": "mean",
    "dpm": "mean",
    "o_dpm": "mean",
    "d_Assists_PerGame": "mean",
    "d_Assists_Per100": "mean",
    "netrtg_on_off": "mean",
    "GamesPlayed": "sum",
    "Minutes": "sum",
    "year": ["min", "max", "count"],
}).round(3)

# 展平列名
career.columns = [f"{a}_{b}" if b != "mean" and b != "sum" else a
                   for a, b in career.columns]
career = career.rename(columns={"year_min": "from_year", "year_max": "to_year", "year_count": "seasons"})
career = career.reset_index()

print("=" * 70)
print("CAREER AVERAGES (from databallr real data)")
print("=" * 70)
display_cols = ["player_name", "from_year", "to_year", "seasons",
                "d_Points_PerGame", "d_Points_Per100", "TS_pct", "rTSPct",
                "d_Points_Created_PerGame", "o_dpm", "netrtg_on_off", "GamesPlayed"]
print(career[display_cols].to_string(index=False))
print()

# ── 3. 巅峰赛季分析（每人最好的5个赛季） ──
print("=" * 70)
print("PEAK SEASONS (Top 5 by O-DPM for each player)")
print("=" * 70)

peak_rows = []
for player in df["player_name"].unique():
    player_df = df[df["player_name"] == player].nlargest(5, "o_dpm")
    peak_rows.append({
        "player": player,
        "peak_years": f"{player_df['year'].min()}-{player_df['year'].max()}",
        "PPG": player_df["d_Points_PerGame"].mean(),
        "P100": player_df["d_Points_Per100"].mean(),
        "TS": player_df["TS_pct"].mean(),
        "rTS": player_df["rTSPct"].mean(),
        "PtsCreated": player_df["d_Points_Created_PerGame"].mean(),
        "PtsCreated100": player_df["d_Points_Created_Per100"].mean(),
        "O_DPM": player_df["o_dpm"].mean(),
        "DPM": player_df["dpm"].mean(),
        "APG": player_df["d_Assists_PerGame"].mean(),
        "OnOff": player_df["netrtg_on_off"].mean(),
        "GP": player_df["GamesPlayed"].sum(),
    })

peak = pd.DataFrame(peak_rows).round(3)
print(peak[["player", "peak_years", "PPG", "P100", "TS", "rTS",
            "PtsCreated", "O_DPM", "DPM", "OnOff"]].to_string(index=False))
print()

# ── 4. MODEL: 加权评分 ──
features = ["P100", "rTS", "PtsCreated100", "O_DPM", "OnOff"]
scaler = StandardScaler()
X = scaler.fit_transform(peak[features])

# 权重设计:
#   P100:           0.20  得分产量 (Pace修正后)
#   rTS:            0.15  相对效率 (已经是联盟平均修正后的)
#   PtsCreated/100: 0.20  创造得分 (替代我们之前的BoxCreation)
#   O-DPM:          0.25  进攻影响力 (最权威的综合指标)
#   On-Off:         0.20  实际场上影响
weights = np.array([0.20, 0.15, 0.20, 0.25, 0.20])

peak["Score"] = X @ weights
peak["Rank"] = peak["Score"].rank(ascending=False).astype(int)
peak = peak.sort_values("Rank")

print("=" * 70)
print("FINAL RANKING (Peak 5 Seasons, Weighted Model)")
print("=" * 70)
result = peak[["Rank", "player", "peak_years", "PPG", "P100", "rTS",
               "PtsCreated", "O_DPM", "OnOff", "Score"]].copy()
result["Score"] = result["Score"].round(4)
print(result.to_string(index=False))
print()

# ── 5. Ridge Regression ──
print("=" * 70)
print("RIDGE REGRESSION (O_DPM as target)")
print("=" * 70)

features_r = ["P100", "rTS", "PtsCreated100", "OnOff"]
Xr = StandardScaler().fit_transform(peak[features_r])
yr = peak["O_DPM"].values

ridge = Ridge(alpha=1.0)
ridge.fit(Xr, yr)

for f, c in zip(features_r, ridge.coef_):
    print(f"  {f:20s}: {c:+.4f}")
print(f"  {'intercept':20s}: {ridge.intercept_:.4f}")

peak["Score_ridge"] = ridge.predict(Xr)
peak["Rank_ridge"] = peak["Score_ridge"].rank(ascending=False).astype(int)
print()
print(peak.sort_values("Rank_ridge")[["Rank_ridge", "player", "Score_ridge"]].round(4).to_string(index=False))
print()

# ── 6. CAREER averages model ──
print("=" * 70)
print("CAREER AVERAGES RANKING (full career, not just peak)")
print("=" * 70)

career_features = ["d_Points_Per100", "rTSPct", "d_Points_Created_Per100",
                    "o_dpm", "netrtg_on_off"]
Xc = StandardScaler().fit_transform(career[career_features])
career["Score"] = Xc @ weights
career["Rank"] = career["Score"].rank(ascending=False).astype(int)
career = career.sort_values("Rank")
print(career[["Rank", "player_name", "seasons", "d_Points_PerGame",
              "rTSPct", "o_dpm", "netrtg_on_off", "Score"]].round(3).to_string(index=False))
print()

# ── 7. 敏感性分析 ──
print("=" * 70)
print("SENSITIVITY ANALYSIS (weights +/-15%)")
print("=" * 70)

base_w = weights.copy()
sens = {}
for i, fname in enumerate(features):
    for d in [+0.15, -0.15]:
        w = base_w.copy()
        w[i] *= (1 + d)
        w /= w.sum()
        scores = X @ w
        ranks = pd.Series(scores).rank(ascending=False).astype(int).values
        sens[f"{fname} {'+' if d>0 else ''}{d*100:.0f}%"] = ranks

sens_df = pd.DataFrame(sens, index=peak["player"].values)
sens_df["std"] = sens_df.std(axis=1).round(2)
print(sens_df.to_string())
print()

# ── 8. 保存 ──
peak.sort_values("Rank").to_csv("results/ranking_databallr.csv", index=False)
print("-> Peak ranking saved to results/ranking_databallr.csv")
print()
print("=" * 70)
print("DATA SOURCES")
print("=" * 70)
print("All data from: databallr.com API (2001-2026)")
print("Metrics: Points, TS%, rTS%, PtsCreated, O-DPM, DPM, On-Off, Assists")
print("Note: Wilt Chamberlain & Kareem Abdul-Jabbar not available (pre-2001)")
