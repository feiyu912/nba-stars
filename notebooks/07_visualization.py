"""
可视化: 4张精美图表
===================
1. TOP 20 得分能力排名 (横向条形图)
2. 得分结构拆解 (堆叠柱状图: 2P/3P/FT)
3. 得分 vs 影响力 象限图 (散点图)
4. 季后赛表现 vs 常规赛 (箭头图)
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# 字体设置
matplotlib.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 12

# 加载数据
reg = pd.read_csv("data/nba100_career_all.csv")
po = pd.read_csv("data/nba100_playoffs.csv")
scoring = pd.read_csv("results/scoring_ranking.csv")
impact = pd.read_csv("results/impact_ranking.csv")

# 准备得分结构数据
career = reg.groupby("player").agg({
    "PPG": "mean", "FGM": "mean", "FG3M": "mean",
    "FTM": "mean", "TS_pct": "mean", "GP": "sum",
    "APG": "mean",
}).round(3).reset_index()
career["FG3M"] = career["FG3M"].fillna(0)
career["FG2M"] = career["FGM"] - career["FG3M"]
career["pts_2P"] = career["FG2M"] * 2
career["pts_3P"] = career["FG3M"] * 3
career["pts_FT"] = career["FTM"] * 1
career["pts_total"] = career["pts_2P"] + career["pts_3P"] + career["pts_FT"]
career["pct_2P"] = career["pts_2P"] / career["pts_total"] * 100
career["pct_3P"] = career["pts_3P"] / career["pts_total"] * 100
career["pct_FT"] = career["pts_FT"] / career["pts_total"] * 100

career = career.merge(scoring[["player", "scoring_rank"]], on="player", how="left")
career = career.merge(impact[["player", "impact_rank"]], on="player", how="left")

# 季后赛数据
po_avg = po.groupby("player").agg({"PPG": "mean", "GP": "sum"}).round(2).reset_index()
po_avg.columns = ["player", "po_PPG", "po_GP"]
career = career.merge(po_avg, on="player", how="left")

# 颜色方案
COLORS = {
    "2P": "#2196F3",   # 蓝
    "3P": "#FF9800",   # 橙
    "FT": "#9E9E9E",   # 灰
    "bg": "#1a1a2e",   # 深色背景
    "text": "#e0e0e0",
    "accent": "#00bcd4",
    "gold": "#ffd700",
}

fig = plt.figure(figsize=(18, 28), facecolor=COLORS["bg"])

# ════════════════════════════════
# 图1: TOP 20 得分能力排名
# ════════════════════════════════
ax1 = fig.add_subplot(4, 1, 1)
ax1.set_facecolor(COLORS["bg"])

top20 = career.sort_values("scoring_rank").head(20).iloc[::-1]  # 反转让#1在最上面

colors = []
for _, r in top20.iterrows():
    rk = r["scoring_rank"]
    if rk <= 3: colors.append(COLORS["gold"])
    elif rk <= 10: colors.append(COLORS["accent"])
    else: colors.append("#5c6bc0")

bars = ax1.barh(range(len(top20)), top20["PPG"], color=colors, height=0.7, alpha=0.9)

for i, (_, r) in enumerate(top20.iterrows()):
    ax1.text(r["PPG"] + 0.3, i, f'{r["PPG"]:.1f}', va='center',
             color=COLORS["text"], fontsize=10, fontweight='bold')

ax1.set_yticks(range(len(top20)))
ax1.set_yticklabels([f'#{int(r["scoring_rank"])} {r["player"]}' for _, r in top20.iterrows()],
                     fontsize=11, color=COLORS["text"])
ax1.set_xlabel("Career PPG", fontsize=12, color=COLORS["text"])
ax1.set_title("TOP 20 Scoring Ability Ranking", fontsize=16, color=COLORS["gold"],
              fontweight='bold', pad=15)
ax1.tick_params(colors=COLORS["text"])
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.spines['bottom'].set_color(COLORS["text"])
ax1.spines['left'].set_color(COLORS["text"])

# ════════════════════════════════
# 图2: 得分结构 (堆叠柱状图)
# ════════════════════════════════
ax2 = fig.add_subplot(4, 1, 2)
ax2.set_facecolor(COLORS["bg"])

top15 = career.sort_values("scoring_rank").head(15)
names = [p.split()[-1] for p in top15["player"]]  # 只用姓
x = np.arange(len(names))
w = 0.6

ax2.bar(x, top15["pct_2P"], w, label="2-Point", color=COLORS["2P"], alpha=0.9)
ax2.bar(x, top15["pct_3P"], w, bottom=top15["pct_2P"], label="3-Point", color=COLORS["3P"], alpha=0.9)
ax2.bar(x, top15["pct_FT"], w, bottom=top15["pct_2P"] + top15["pct_3P"],
        label="Free Throw", color=COLORS["FT"], alpha=0.7)

ax2.set_xticks(x)
ax2.set_xticklabels(names, rotation=45, ha='right', fontsize=10, color=COLORS["text"])
ax2.set_ylabel("% of Scoring", fontsize=12, color=COLORS["text"])
ax2.set_title("Scoring Breakdown: Where Do Points Come From?", fontsize=16,
              color=COLORS["gold"], fontweight='bold', pad=15)
ax2.legend(loc='upper right', fontsize=10, facecolor=COLORS["bg"],
           edgecolor=COLORS["text"], labelcolor=COLORS["text"])
ax2.set_ylim(0, 105)
ax2.tick_params(colors=COLORS["text"])
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['bottom'].set_color(COLORS["text"])
ax2.spines['left'].set_color(COLORS["text"])

# ════════════════════════════════
# 图3: 得分 vs 影响力 象限图
# ════════════════════════════════
ax3 = fig.add_subplot(4, 1, 3)
ax3.set_facecolor(COLORS["bg"])

both = career[(career["scoring_rank"].notna()) & (career["impact_rank"].notna())].copy()
both = both[both["scoring_rank"] <= 50]  # 只看前50

# 反转轴 (排名越小越好)
x_vals = both["scoring_rank"]
y_vals = both["impact_rank"]

scatter = ax3.scatter(x_vals, y_vals, s=80, c=COLORS["accent"], alpha=0.7, edgecolors='white', linewidth=0.5)

# 标注关键球员
key_players = ["Michael Jordan", "LeBron James", "Stephen Curry", "Kevin Durant",
               "Kobe Bryant", "Shaquille O'Neal", "James Harden", "Nikola Jokic",
               "Magic Johnson", "Steve Nash", "Luka Doncic", "Carmelo Anthony"]
for _, r in both.iterrows():
    if r["player"] in key_players:
        name = r["player"].split()[-1]
        ax3.annotate(name, (r["scoring_rank"], r["impact_rank"]),
                     fontsize=9, color=COLORS["text"], fontweight='bold',
                     xytext=(5, 5), textcoords='offset points')

# 对角线 (排名一致)
ax3.plot([0, 55], [0, 55], '--', color=COLORS["text"], alpha=0.3, linewidth=1)
ax3.text(45, 40, "Balanced", color=COLORS["text"], alpha=0.4, fontsize=9, rotation=45)

# 象限标签
ax3.text(5, 45, "Pure Scorer\n(Score > Impact)", color=COLORS["FT"], fontsize=10, alpha=0.6)
ax3.text(35, 5, "Playmaker\n(Impact > Score)", color=COLORS["3P"], fontsize=10, alpha=0.6)

ax3.set_xlabel("Scoring Rank (lower = better)", fontsize=12, color=COLORS["text"])
ax3.set_ylabel("Impact Rank (lower = better)", fontsize=12, color=COLORS["text"])
ax3.set_title("Scoring Ability vs Offensive Impact", fontsize=16,
              color=COLORS["gold"], fontweight='bold', pad=15)
ax3.set_xlim(0, 55)
ax3.set_ylim(0, 55)
ax3.invert_xaxis()
ax3.invert_yaxis()
ax3.tick_params(colors=COLORS["text"])
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.spines['bottom'].set_color(COLORS["text"])
ax3.spines['left'].set_color(COLORS["text"])

# ════════════════════════════════
# 图4: 季后赛 vs 常规赛 表现
# ════════════════════════════════
ax4 = fig.add_subplot(4, 1, 4)
ax4.set_facecolor(COLORS["bg"])

playoff = career[career["po_GP"] > 50].copy()
playoff["delta"] = playoff["po_PPG"] - playoff["PPG"]
playoff = playoff.sort_values("delta", ascending=False).head(20)

colors4 = [COLORS["gold"] if d > 0 else "#e74c3c" for d in playoff["delta"]]
names4 = [p.split()[-1] for p in playoff["player"]]

bars4 = ax4.barh(range(len(playoff)), playoff["delta"], color=colors4, height=0.7, alpha=0.9)

for i, (_, r) in enumerate(playoff.iterrows()):
    sign = "+" if r["delta"] > 0 else ""
    ax4.text(r["delta"] + (0.1 if r["delta"] > 0 else -0.1), i,
             f'{sign}{r["delta"]:.1f}', va='center',
             color=COLORS["text"], fontsize=9, fontweight='bold',
             ha='left' if r["delta"] > 0 else 'right')

ax4.set_yticks(range(len(playoff)))
ax4.set_yticklabels(names4, fontsize=10, color=COLORS["text"])
ax4.axvline(x=0, color=COLORS["text"], linewidth=0.5, alpha=0.5)
ax4.set_xlabel("Playoff PPG - Regular PPG", fontsize=12, color=COLORS["text"])
ax4.set_title("Playoff Performance: Who Steps Up?", fontsize=16,
              color=COLORS["gold"], fontweight='bold', pad=15)
ax4.tick_params(colors=COLORS["text"])
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.spines['bottom'].set_color(COLORS["text"])
ax4.spines['left'].set_color(COLORS["text"])

# 保存
plt.tight_layout(pad=3.0)
plt.savefig("results/scoring_analysis.png", dpi=150, facecolor=COLORS["bg"],
            bbox_inches='tight')
print("-> results/scoring_analysis.png")
plt.close()
