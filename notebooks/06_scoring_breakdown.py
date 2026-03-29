"""
得分结构拆解 + DPM对标
=======================
1. 每个球员的得分来源: 两分/三分/罚球 占比
2. 得分方式雷达: 产量/效率/季后赛/投篮纯度
3. 与 O-DPM 对标: 我们的排名 vs 专业指标
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

scoring = pd.read_csv("results/scoring_ranking.csv")

# ══════════════════════════════════════════
# PART 1: 得分结构拆解
# ══════════════════════════════════════════
print("=" * 90)
print("SCORING BREAKDOWN: 得分结构拆解")
print("=" * 90)
print("""
每个球员的得分从哪来？
  2P = 两分球命中 × 2
  3P = 三分球命中 × 3
  FT = 罚球命中 × 1

占比 = 该来源得分 / 总得分
""")

# 常规赛得分结构
career = reg.groupby("player").agg({
    "PPG": "mean", "FGM": "mean", "FG3M": "mean",
    "FTM": "mean", "FGA": "mean", "FG3A": "mean",
    "FTA": "mean", "TS_pct": "mean", "GP": "sum",
}).round(3).reset_index()

# 拆解得分来源
career["FG3M"] = career["FG3M"].fillna(0)
career["FG2M"] = career["FGM"] - career["FG3M"]

career["pts_2P"] = career["FG2M"] * 2
career["pts_3P"] = career["FG3M"] * 3
career["pts_FT"] = career["FTM"] * 1
career["pts_total"] = career["pts_2P"] + career["pts_3P"] + career["pts_FT"]

career["pct_2P"] = (career["pts_2P"] / career["pts_total"] * 100).round(1)
career["pct_3P"] = (career["pts_3P"] / career["pts_total"] * 100).round(1)
career["pct_FT"] = (career["pts_FT"] / career["pts_total"] * 100).round(1)

# 合并排名
career = career.merge(scoring[["player", "scoring_rank"]], on="player", how="left")
career = career.sort_values("scoring_rank")

print(f"{'Rk':>3s}  {'Player':28s} {'PPG':>5s}  "
      f"{'2P%':>5s} {'3P%':>5s} {'FT%':>5s}  {'得分类型'}")
print("-" * 80)

for _, r in career.head(40).iterrows():
    # 分类
    if r["pct_3P"] > 30:
        stype = "三分型"
    elif r["pct_FT"] > 28:
        stype = "罚球型"
    elif r["pct_2P"] > 70:
        stype = "中近距离型"
    else:
        stype = "均衡型"

    bar_2 = "█" * int(r["pct_2P"] / 5)
    bar_3 = "▓" * int(r["pct_3P"] / 5)
    bar_f = "░" * int(r["pct_FT"] / 5)

    rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f" {rk:3d}  {r['player']:28s} {r['PPG']:5.1f}  "
          f"{r['pct_2P']:5.1f} {r['pct_3P']:5.1f} {r['pct_FT']:5.1f}  "
          f"{bar_2}{bar_3}{bar_f} {stype}")

# ══════════════════════════════════════════
# PART 2: 得分"纯度"指标
# ══════════════════════════════════════════
print()
print("=" * 90)
print("SCORING PURITY: 得分纯度 (投篮得分占比)")
print("=" * 90)
print("""
纯度 = (2P得分 + 3P得分) / 总得分
越高 = 越靠真实投篮得分, 而不是罚球

纯度高(>85%): 靠投篮技术, 不依赖裁判
纯度低(<72%): 大量依赖罚球
""")

career["purity"] = (100 - career["pct_FT"]).round(1)
career = career.sort_values("purity", ascending=False)

print(f"\n最纯(投篮为主):")
for _, r in career.head(10).iterrows():
    rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f"  #{rk:3d} {r['player']:28s}  纯度={r['purity']:.1f}%  "
          f"(2P:{r['pct_2P']:.0f}% 3P:{r['pct_3P']:.0f}% FT:{r['pct_FT']:.0f}%)")

print(f"\n最不纯(罚球依赖):")
for _, r in career.tail(10).iterrows():
    rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f"  #{rk:3d} {r['player']:28s}  纯度={r['purity']:.1f}%  "
          f"(2P:{r['pct_2P']:.0f}% 3P:{r['pct_3P']:.0f}% FT:{r['pct_FT']:.0f}%)")

# ══════════════════════════════════════════
# PART 3: 季后赛得分变化
# ══════════════════════════════════════════
print()
print("=" * 90)
print("PLAYOFF PERFORMANCE: 大赛表现 (季后赛 vs 常规赛)")
print("=" * 90)

po_avg = po.groupby("player").agg({
    "PPG": "mean", "GP": "sum",
}).round(2).reset_index()
po_avg.columns = ["player", "po_PPG", "po_GP"]

reg_avg = reg.groupby("player")["PPG"].mean().round(2).reset_index()
reg_avg.columns = ["player", "reg_PPG"]

perf = reg_avg.merge(po_avg, on="player", how="left")
perf = perf.merge(scoring[["player", "scoring_rank"]], on="player", how="left")
perf["delta"] = (perf["po_PPG"] - perf["reg_PPG"]).round(2)
perf["delta_pct"] = ((perf["delta"] / perf["reg_PPG"]) * 100).round(1)

print(f"\n季后赛得分上升最多 (大赛型):")
clutch = perf[perf["po_GP"] > 50].sort_values("delta", ascending=False)
for _, r in clutch.head(10).iterrows():
    rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f"  #{rk:3d} {r['player']:28s}  "
          f"常规={r['reg_PPG']:5.1f} → 季后={r['po_PPG']:5.1f}  "
          f"({r['delta']:+.1f}, {r['delta_pct']:+.1f}%)")

print(f"\n季后赛得分下降最多 (50+场):")
for _, r in clutch.tail(10).iterrows():
    rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else 0
    print(f"  #{rk:3d} {r['player']:28s}  "
          f"常规={r['reg_PPG']:5.1f} → 季后={r['po_PPG']:5.1f}  "
          f"({r['delta']:+.1f}, {r['delta_pct']:+.1f}%)")

# ══════════════════════════════════════════
# PART 4: 与 O-DPM 对标
# ══════════════════════════════════════════
print()
print("=" * 90)
print("MODEL COMPARISON: 我们的排名 vs O-DPM (专业指标)")
print("=" * 90)
print("""
O-DPM 是 databallr.com 的进攻影响力指标 (统计学家设计)
如果我们的得分排名和 O-DPM 趋势一致 → 模型有效
如果差异大但可解释 → 说明我们捕捉了不同维度
""")

db_career = db.groupby("player_name").agg({
    "o_dpm": "mean",
}).round(3).reset_index()
db_career.columns = ["player", "o_dpm"]
db_career["odpm_rank"] = db_career["o_dpm"].rank(ascending=False).astype(int)

compare = scoring[["player", "scoring_rank"]].merge(db_career, on="player", how="inner")
compare["diff"] = compare["odpm_rank"] - compare["scoring_rank"]
compare = compare.sort_values("scoring_rank")

# 相关性
corr = compare["scoring_rank"].corr(compare["odpm_rank"])
print(f"\n相关性: r = {corr:.3f}")
if corr > 0.7:
    print("→ 高度一致: 我们的模型和专业指标方向相同")
elif corr > 0.4:
    print("→ 中等一致: 整体方向相同, 但存在有意义的差异")
else:
    print("→ 低相关: 我们衡量的东西和O-DPM不同 (预期内, 因为我们只看得分)")

print(f"\n{'Player':28s} {'我们':>4s} {'O-DPM':>6s} {'差值':>5s}  {'解读'}")
print("-" * 65)
for _, r in compare.head(30).iterrows():
    d = int(r["diff"])
    if d < -10:
        note = "O-DPM更认可 (可能因为助攻/引力)"
    elif d > 10:
        note = "我们更认可 (纯得分能力更强)"
    else:
        note = "基本一致"
    print(f"  {r['player']:28s} #{int(r['scoring_rank']):3d}  #{int(r['odpm_rank']):3d}  "
          f"{d:+4d}   {note}")

print(f"\n差异最大的球员 (我们看重得分, O-DPM看重整体影响):")
for _, r in compare.nlargest(5, "diff").iterrows():
    print(f"  {r['player']:28s}  我们#{int(r['scoring_rank']):3d} vs O-DPM#{int(r['odpm_rank']):3d}  "
          f"→ 纯得分手, 影响力被O-DPM低估")
for _, r in compare.nsmallest(5, "diff").iterrows():
    print(f"  {r['player']:28s}  我们#{int(r['scoring_rank']):3d} vs O-DPM#{int(r['odpm_rank']):3d}  "
          f"→ 组织/引力型, 得分之外有价值")
