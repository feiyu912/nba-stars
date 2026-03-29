"""
NBA 101-Player Scoring Ability Ranking
=======================================
目标变量: PtsCreated (创造得分)
  = 自己得的分 + 助攻直接产生的分
  助攻的权重是自然的(一次助攻=2-3分), 不会被人为放大

方法:
  1. 用53个现代球员训练: 基础数据 → 预测 PtsCreated
  2. 模型自动学出权重
  3. 套用到全部101人
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# ── 1. 加载数据 ──
nba = pd.read_csv("data/nba100_career_all.csv")
db = pd.read_csv("data/nba100_databallr.csv")
db["player_name"] = db["player_name"].replace({
    "Luka Dončić": "Luka Doncic",
    "Nikola Jokić": "Nikola Jokic",
    "Jimmy Butler III": "Jimmy Butler",
})

# ── 2. NBA API 生涯平均 ──
nba["year"] = nba["season"].str[:4].astype(int)
nba["TS_pct"] = nba["PPG"] / (2 * (nba["FGA"] + 0.44 * nba["FTA"]))
nba["FTR"] = nba["FTA"] / nba["FGA"]

career = nba.groupby("player").agg({
    "PPG": "mean", "TS_pct": "mean", "APG": "mean",
    "RPG": "mean", "TOV": "mean", "FTR": "mean",
    "MIN": "mean", "GP": "sum", "FGA": "mean",
    "season": "count",
}).round(4)
career.columns = ["PPG", "TS_pct", "APG", "RPG", "TOV", "FTR",
                   "MPG", "GP", "FGA", "seasons"]
career = career.reset_index()

# 巅峰5年PPG
peak_ppg = nba.groupby("player")["PPG"].apply(
    lambda x: x.nlargest(5).mean()
).round(2).reset_index()
peak_ppg.columns = ["player", "peak_PPG"]
career = career.merge(peak_ppg, on="player")

for col in ["TOV", "FTR"]:
    career[col] = career[col].fillna(career[col].median())

# ── 3. databallr: PtsCreated 作为目标 ──
db_career = db.groupby("player_name").agg({
    "d_Points_Created_PerGame": "mean",
    "d_Points_Created_Per100": "mean",
    "o_dpm": "mean",
    "dpm": "mean",
    "netrtg_on_off": "mean",
}).round(3).reset_index()
db_career.columns = ["player", "PtsCreated", "PtsCreated100",
                       "o_dpm", "dpm", "onoff"]

career = career.merge(db_career, on="player", how="left")

# ── 4. 训练 ──
train = career[career["PtsCreated"].notna()].copy()

print("=" * 70)
print("STEP 1: 学习权重 — 哪些数据预测'创造得分'?")
print(f"目标: PtsCreated (自己得分 + 助攻产生的分)")
print(f"训练集: {len(train)} players")
print("=" * 70)

features = ["PPG", "TS_pct", "APG", "FGA", "FTR", "TOV", "peak_PPG"]
X_train = train[features].values
y_train = train["PtsCreated"].values

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)

ridge = Ridge(alpha=2.0)
ridge.fit(X_train_s, y_train)

print("\n数据学到的权重:")
coefs = pd.Series(ridge.coef_, index=features)
pcts = (coefs.abs() / coefs.abs().sum() * 100).round(1)
for f in features:
    bar = "#" * int(pcts[f] / 2)
    direction = "越高越好" if coefs[f] > 0 else "越低越好"
    print(f"  {f:12s}: {coefs[f]:+.3f}  ({pcts[f]:5.1f}%)  {bar}  {direction}")

print(f"\n  R² = {ridge.score(X_train_s, y_train):.4f}")

# 交叉验证
loo = LeaveOneOut()
y_cv = []
for tr_idx, te_idx in loo.split(X_train_s):
    r = Ridge(alpha=2.0).fit(X_train_s[tr_idx], y_train[tr_idx])
    y_cv.append(r.predict(X_train_s[te_idx])[0])

cv_r2 = r2_score(y_train, y_cv)
cv_mae = mean_absolute_error(y_train, y_cv)
print(f"  CV R² = {cv_r2:.4f}, MAE = ±{cv_mae:.1f}分")

# ── 5. 预测全部101人 ──
print()
print("=" * 70)
print("STEP 2: 全部101人排名")
print("=" * 70)

X_all = scaler.transform(career[features].values)
career["predicted_PtsC"] = ridge.predict(X_all)
career["rank"] = career["predicted_PtsC"].rank(ascending=False).astype(int)
career = career.sort_values("rank")

print(f"\n{'Rk':>3s}  {'Player':28s} {'GP':>5s} "
      f"{'PPG':>5s} {'TS%':>5s} {'APG':>4s}  "
      f"{'Pred':>6s} {'Actual':>7s}")
print("-" * 75)
for _, r in career.iterrows():
    actual = f"{r['PtsCreated']:5.1f}" if pd.notna(r.get("PtsCreated")) else "  N/A"
    print(f" {int(r['rank']):3d}  {r['player']:28s} {int(r['GP']):5d} "
          f"{r['PPG']:5.1f} {r['TS_pct']:.3f} {r['APG']:4.1f}  "
          f"{r['predicted_PtsC']:5.1f}  {actual}")

# ── 6. 合理性检查 ──
print()
print("=" * 70)
print("SANITY CHECKS")
print("=" * 70)

checks = {
    "Michael Jordan": (1, 5),
    "LeBron James": (1, 10),
    "Wilt Chamberlain": (1, 15),
    "Kevin Durant": (1, 10),
    "Stephen Curry": (3, 15),
    "Kobe Bryant": (5, 20),
    "Larry Bird": (5, 25),
    "Shaquille O'Neal": (10, 35),
    "Dennis Rodman": (90, 101),
    "Bill Russell": (60, 101),
}

all_pass = True
for name, (lo, hi) in checks.items():
    r = career[career["player"] == name]
    if len(r):
        rank = int(r.iloc[0]["rank"])
        ok = lo <= rank <= hi
        if not ok: all_pass = False
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:28s}  #{rank:3d}  (expected #{lo}-{hi})")

print(f"\n  {'ALL PASS' if all_pass else 'SOME FAILED'}")

# ── 7. 验证: 预测 vs 实际 ──
print()
print("=" * 70)
print("STEP 3: 模型预测 vs 实际 (53个有数据的球员)")
print("=" * 70)

t = career[career["PtsCreated"].notna()].copy()
t["gap"] = t["PtsCreated"] - t["predicted_PtsC"]
print(f"\n隐藏价值 (实际 > 预测):")
for _, r in t.nlargest(5, "gap").iterrows():
    print(f"  {r['player']:24s}  实际={r['PtsCreated']:5.1f}  预测={r['predicted_PtsC']:5.1f}  差={r['gap']:+.1f}")

print(f"\n数据虚高 (预测 > 实际):")
for _, r in t.nsmallest(5, "gap").iterrows():
    print(f"  {r['player']:24s}  实际={r['PtsCreated']:5.1f}  预测={r['predicted_PtsC']:5.1f}  差={r['gap']:+.1f}")

# ── 8. 分档 ──
print()
print("=" * 70)
print("TIERS")
print("=" * 70)

tiers = [
    (1, 5, "S-Tier"),
    (6, 15, "A-Tier"),
    (16, 30, "B-Tier"),
    (31, 55, "C-Tier"),
    (56, 80, "D-Tier"),
    (81, 101, "E-Tier"),
]

for lo, hi, label in tiers:
    t = career[(career["rank"] >= lo) & (career["rank"] <= hi)]
    print(f"\n--- {label} ---")
    for _, r in t.iterrows():
        flag = "*" if pd.notna(r.get("PtsCreated")) else " "
        print(f"  #{int(r['rank']):3d}{flag} {r['player']:28s}  "
              f"PPG={r['PPG']:5.1f}  PtsC={r['predicted_PtsC']:5.1f}")

career.to_csv("results/nba100_ranking_fixed.csv", index=False)
print(f"\n-> results/nba100_ranking_fixed.csv")
