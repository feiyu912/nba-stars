"""
从 stat-nba.com 获取历史生涯高阶数据
覆盖: 1951-至今所有球员（解决张伯伦/贾巴尔/乔丹巅峰期数据缺失问题）
"""
import time
import requests
import pandas as pd
from io import StringIO

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Cookie': 'Hm_lvt_102e5c22af038a553a8610096bcc8bd4=1774719271; HMACCOUNT=AB47F31410224AE4; Hm_lpvt_102e5c22af038a553a8610096bcc8bd4=1774719473',
    'Host': 'www.stat-nba.com',
    'Referer': 'http://www.stat-nba.com/award/item13.html',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
}

BASE_URL = "http://www.stat-nba.com/award.php"

# 要抓取的高阶指标
METRICS = {
    "PER":   {"keyItem": "per",    "keyTable": "advanced"},
    "WS48":  {"keyItem": "ws48",   "keyTable": "advanced"},
    "USG":   {"keyItem": "usgper", "keyTable": "advanced"},
    "AST%":  {"keyItem": "astper", "keyTable": "advanced"},
    "OWS":   {"keyItem": "ows",    "keyTable": "advanced"},
    "DWS":   {"keyItem": "dws",    "keyTable": "advanced"},
    "WS":    {"keyItem": "ws",     "keyTable": "advanced"},
    "ORTG":  {"keyItem": "ortg",   "keyTable": "per_poss"},
    "DRTG":  {"keyItem": "drtg",   "keyTable": "per_poss"},
    "TOV%":  {"keyItem": "tovper", "keyTable": "advanced"},
}

def fetch_all_metrics(isnba, label):
    """抓取常规赛(isnba=1)或季后赛(isnba=0)的高阶数据"""
    dfs = {}
    for metric_name, params in METRICS.items():
        query = {
            "item": 13,
            "keyItem": params["keyItem"],
            "keyTable": params["keyTable"],
            "isnba": isnba,
            "season": -1,
        }
        print(f"  [{label}] Fetching {metric_name}...", end=" ")
        try:
            r = requests.get(BASE_URL, params=query, headers=HEADERS, verify=False, timeout=15)
            r.encoding = 'utf-8'
            if len(r.text) < 500:
                print(f"empty ({len(r.text)} chars)")
                continue
            tables = pd.read_html(StringIO(r.text), flavor='lxml')
            if tables:
                t = tables[0]
                last_col = t.columns[-1]
                t = t[["球员", last_col]].rename(columns={"球员": "player_cn", last_col: metric_name})
                dfs[metric_name] = t
                print(f"OK ({len(t)} players)")
            else:
                print("no table found")
        except Exception as e:
            print(f"ERROR: {e}")
        time.sleep(0.5)
    return dfs

# ── 常规赛 ──
print("=== REGULAR SEASON (isnba=1) ===")
reg_dfs = fetch_all_metrics(isnba=1, label="regular")

# ── 季后赛 ──
print("\n=== PLAYOFFS (isnba=0) ===")
po_dfs = fetch_all_metrics(isnba=0, label="playoffs")

# 抓完整基础数据（常规赛 + 季后赛）
def fetch_base(url, label):
    print(f"\nFetching {label} base stats...", end=" ")
    r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
    r.encoding = 'utf-8'
    tables = pd.read_html(StringIO(r.text), flavor='lxml')
    if tables:
        t = tables[0]
        t = t.rename(columns={
            "Unnamed: 0": "rank", "球员": "player_cn",
            "出场": "GP", "时间": "MPG", "得分": "PPG",
            "篮板": "RPG", "助攻": "APG", "抢断": "SPG",
            "盖帽": "BPG", "失误": "TOV", "效率值PER": "PER_base",
            "投篮": "FG_pct_str", "三分": "FG3_pct_str", "罚球": "FT_pct_str",
        })
        print(f"OK ({len(t)} players)")
        return t
    print("FAILED")
    return pd.DataFrame()

base = fetch_base("http://www.stat-nba.com/award/item13.html", "regular season")
base_po = fetch_base(
    "http://www.stat-nba.com/award.php?item=13&keyItem=per&keyTable=advanced&isnba=0&season=-1",
    "playoffs"
)
all_dfs = reg_dfs  # 后续合并用常规赛

CN_TO_EN = {
    "迈克尔-乔丹": "Michael Jordan",
    "勒布朗-詹姆斯": "LeBron James",
    "斯蒂芬-库里": "Stephen Curry",
    "凯文-杜兰特": "Kevin Durant",
    "沙奎尔-奥尼尔": "Shaquille O'Neal",
    "卡里姆-贾巴尔": "Kareem Abdul-Jabbar",
    "威尔特-张伯伦": "Wilt Chamberlain",
    "科比-布莱恩特": "Kobe Bryant",
    "詹姆斯-哈登": "James Harden",
    "卢卡-东契奇": "Luka Doncic",
}

def merge_data(base_df, metric_dfs, suffix=""):
    """合并基础数据和各项高阶指标"""
    cols = ["player_cn", "GP", "MPG", "PPG", "RPG", "APG", "PER_base"]
    merged = base_df[[c for c in cols if c in base_df.columns]].copy()
    for name, mdf in metric_dfs.items():
        if name == "PER":
            continue
        if suffix:
            mdf = mdf.rename(columns={name: name + suffix})
        merged = merged.merge(mdf, on="player_cn", how="left")
    merged["player_en"] = merged["player_cn"].map(CN_TO_EN)
    return merged

# ── 合并常规赛 ──
print("\nMerging regular season...")
reg = merge_data(base, reg_dfs)
reg_target = reg[reg["player_en"].notna()].sort_values("PER_base", ascending=False)

print("\n" + "=" * 80)
print("REGULAR SEASON - Target Players")
print("=" * 80)
print(reg_target.to_string(index=False))

# ── 合并季后赛 ──
print("\nMerging playoffs...")
if not base_po.empty:
    po = merge_data(base_po, po_dfs)
    po_target = po[po["player_en"].notna()].sort_values("PER_base", ascending=False)

    print("\n" + "=" * 80)
    print("PLAYOFFS - Target Players")
    print("=" * 80)
    print(po_target.to_string(index=False))
else:
    po_target = pd.DataFrame()

# ── 保存 ──
reg.to_csv("data/statnba_regular.csv", index=False)
reg_target.to_csv("data/statnba_regular_targets.csv", index=False)
print(f"\nRegular season: data/statnba_regular.csv ({len(reg)} rows)")

if not po_target.empty:
    po.to_csv("data/statnba_playoffs.csv", index=False)
    po_target.to_csv("data/statnba_playoffs_targets.csv", index=False)
    print(f"Playoffs: data/statnba_playoffs.csv ({len(po)} rows)")
