"""
Playmaking Ranking: 组织能力
============================
谁最擅长为球队创造得分机会？

跟 Scoring 完全独立 — 得分能力看自己进球, 组织能力看给别人创造机会。

方法 (跟Scoring一致的框架):
  视角A: APG × (APG/TOV) — 助攻量 × 助攻质量(助失比)
  视角C: 时代修正版 — Z-score + 竞争强度 + 每分钟

  季后赛3x加权
  时代稀缺性修正 (60年代场均10助攻比现代更难得)
"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# ── 加载 ──
reg = pd.read_csv("data/nba100_career_all.csv")
po = pd.read_csv("data/nba100_playoffs.csv")
db = pd.read_csv("data/nba100_databallr.csv")
db["player_name"] = db["player_name"].replace({
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
})

# 时代参数
PACE, LTS, TEAMS = {}, {}, {}
for y in range(1955, 1965): PACE[y], LTS[y], TEAMS[y] = 125, 0.460, 9
for y in range(1965, 1975): PACE[y], LTS[y], TEAMS[y] = 110, 0.490, 15
for y in range(1975, 1985): PACE[y], LTS[y], TEAMS[y] = 103, 0.520, 23
for y in range(1985, 1995): PACE[y], LTS[y], TEAMS[y] = 95, 0.535, 26
for y in range(1995, 2005): PACE[y], LTS[y], TEAMS[y] = 91, 0.530, 29
for y in range(2005, 2015): PACE[y], LTS[y], TEAMS[y] = 95, 0.545, 30
for y in range(2015, 2026): PACE[y], LTS[y], TEAMS[y] = 100, 0.570, 30

PLAYOFF_MULTIPLIER = 3

def process_playmaking(df):
    """计算组织能力指标"""
    df = df.copy()
    df["year"] = df["season"].str[:4].astype(int)
    df["pace"] = df["year"].map(PACE).fillna(97)
    df["teams"] = df["year"].map(TEAMS).fillna(30)
    df["competition"] = (df["teams"] / 30).pow(0.5)

    # 助攻效率: APG / TOV (助失比)
    if "TOV" not in df.columns:
        df["TOV"] = 2.5  # 季后赛数据没有TOV, 用联盟平均估算
    df["TOV"] = df["TOV"].fillna(2.5)
    df["TOV"] = df["TOV"].replace(0, 0.5)  # 避免除零
    df["ast_tov"] = df["APG"] / df["TOV"]

    # 每分钟助攻
    df["APM"] = df["APG"] / df["MIN"].replace(0, 1)

    # 稀缺性: 同年Z-score
    year_stats = df.groupby("year")["APG"].agg(["mean", "std"]).reset_index()
    year_stats.columns = ["year", "year_apg_mean", "year_apg_std"]
    df = df.merge(year_stats, on="year", how="left")
    df["year_apg_std"] = df["year_apg_std"].replace(0, 1)
    df["apg_zscore"] = (df["APG"] - df["year_apg_mean"]) / df["year_apg_std"]
    df["scarcity"] = 1 + df["apg_zscore"] * 0.1

    # 视角A: APG(pace修正) × 助失比 × 稀缺性
    df["APG_adj"] = df["APG"] * (97 / df["pace"])
    df["playA"] = df["APG_adj"] * df["ast_tov"] * df["scarcity"]

    # 视角C: 每分钟助攻 × 助失比 × 竞争强度 × 稀缺性
    df["playC"] = df["APM"] * df["ast_tov"] * df["competition"] * df["scarcity"]

    return df

def summarize_play(df, prefix):
    """生涯 + 巅峰5年"""
    result = df.groupby("player").agg({
        "APG": "mean", "TOV": "mean", "ast_tov": "mean",
        "GP": "sum", "MIN": "mean",
    }).round(3).reset_index()
    result.columns = ["player", f"{prefix}_APG", f"{prefix}_TOV",
                       f"{prefix}_ast_tov", f"{prefix}_GP", f"{prefix}_MPG"]

    for view in ["playA", "playC"]:
        career_v = df.groupby("player")[view].mean().round(4).reset_index()
        career_v.columns = ["player", f"{prefix}_{view}_career"]
        peak_v = df.groupby("player")[view].apply(
            lambda x: x.nlargest(5).mean()).round(4).reset_index()
        peak_v.columns = ["player", f"{prefix}_{view}_peak"]
        result = result.merge(career_v, on="player").merge(peak_v, on="player")

    return result

# ── 处理 ──
reg = process_playmaking(reg)
po = process_playmaking(po)

reg_sum = summarize_play(reg, "reg")
po_sum = summarize_play(po, "po")

career = reg_sum.merge(po_sum, on="player", how="left")

# 填充季后赛缺失
for col in career.columns:
    if col.startswith("po_") and col != "player":
        career[col] = career[col].fillna(0)

# ── 加权 ──
career["po_weighted_gp"] = career["po_GP"] * PLAYOFF_MULTIPLIER
career["total_weighted_gp"] = career["reg_GP"] + career["po_weighted_gp"]
career["po_weight"] = career["po_weighted_gp"] / career["total_weighted_gp"]
career["reg_weight"] = 1 - career["po_weight"]

for view in ["playA", "playC"]:
    career[f"reg_{view}"] = 0.6 * career[f"reg_{view}_peak"] + 0.4 * career[f"reg_{view}_career"]
    career[f"po_{view}"] = 0.6 * career[f"po_{view}_peak"] + 0.4 * career[f"po_{view}_career"]
    career[f"total_{view}"] = career["reg_weight"] * career[f"reg_{view}"] + \
                               career["po_weight"] * career[f"po_{view}"]
    career[f"total_{view}_rank"] = career[f"total_{view}"].rank(ascending=False).astype(int)

# 最终 = 中位数
career["play_median"] = career[["total_playA_rank", "total_playC_rank"]].median(axis=1)
career["play_rank"] = career["play_median"].rank().astype(int)

# ── 输出 ──
career = career.sort_values("play_rank")

print("=" * 90)
print("PLAYMAKING RANKING: 组织能力 (101 players)")
print("=" * 90)
print("""
组织能力 = 为球队创造得分机会的能力
跟得分完全独立 — 这里看的是你给别人创造了什么

方法:
  A = APG(pace修正) x 助失比 x 稀缺性
  C = APG/MIN x 助失比 x 竞争强度 x 稀缺性
  季后赛3x加权 | 巅峰60% + 生涯40% | 中位数排名
""")

print(f"{'Rk':>3s}  {'Player':28s} {'A':>3s} {'C':>3s}  "
      f"{'APG':>5s} {'TOV':>4s} {'A/T':>4s} {'poAPG':>5s} {'poGP':>4s}")
print("-" * 80)
for _, r in career.iterrows():
    po_apg = f"{r['po_APG']:4.1f}" if r['po_GP'] > 0 else " N/A"
    print(f" {int(r['play_rank']):3d}  {r['player']:28s} "
          f"{int(r['total_playA_rank']):3d} {int(r['total_playC_rank']):3d}  "
          f"{r['reg_APG']:4.1f}  {r['reg_TOV']:3.1f} {r['reg_ast_tov']:3.1f}  "
          f"{po_apg} {int(r['po_GP']):4d}")

# ── 保存 ──
out = career[["play_rank", "player", "reg_APG", "reg_TOV", "reg_ast_tov",
              "po_APG", "po_GP", "total_playA_rank", "total_playC_rank"]].copy()
out.to_csv("results/playmaking_ranking.csv", index=False)
print(f"\n-> results/playmaking_ranking.csv")

# ── 与得分排名交叉 ──
print()
print("=" * 90)
print("CROSS-TABLE: Scoring vs Playmaking")
print("=" * 90)

scoring = pd.read_csv("results/scoring_ranking.csv")
cross = career[["player", "play_rank"]].merge(
    scoring[["player", "scoring_rank"]], on="player", how="left")
cross["type"] = cross.apply(lambda r:
    "Score + Create" if r["scoring_rank"] <= 15 and r["play_rank"] <= 15
    else ("Pure Scorer" if r["scoring_rank"] <= 20 and r["play_rank"] > 30
    else ("Pure Playmaker" if r["play_rank"] <= 15 and r["scoring_rank"] > 30
    else "")), axis=1)
cross = cross.sort_values("play_rank")

print(f"\n{'Player':28s} {'Score':>5s} {'Play':>5s}  {'Type'}")
print("-" * 55)
for _, r in cross.head(30).iterrows():
    sr = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f"  {r['player']:28s} #{sr:3d}  #{int(r['play_rank']):3d}   {r['type']}")
