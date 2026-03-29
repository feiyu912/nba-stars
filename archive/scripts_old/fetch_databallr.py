"""
从 databallr.com API 获取 2001-2026 真实高阶数据
数据源: https://api.databallr.com
"""
import time
import json
import requests
import pandas as pd

# 我们的目标球员 nba_id（来自 nba_api 验证）
TARGET_IDS = {
    893: "Michael Jordan",       # 2001-2003
    2544: "LeBron James",        # 2004-2026
    201939: "Stephen Curry",     # 2010-2026
    201142: "Kevin Durant",      # 2008-2026
    406: "Shaquille O'Neal",     # 2001-2011
    977: "Kobe Bryant",          # 2001-2016
    201935: "James Harden",      # 2010-2026
    1629029: "Luka Doncic",      # 2019-2026
}

BASE_URL = "https://api.databallr.com/api/supabase/player_stats_with_metrics"

FIELDS = ",".join([
    "player_name", "nba_id", "TeamAbbreviation", "Minutes", "Pos2",
    "year", "playoffs", "GamesPlayed",
    "d_Points_PerGame", "d_Points_Per100",
    "TS_pct", "rTSPct",
    "d_Points_Created_PerGame", "d_Points_Created_Per100",
    "dpm", "o_dpm",
    "d_Assists_PerGame", "d_Assists_Per100",
    "netrtg_on_off",
])

all_data = []

for year in range(2001, 2027):
    print(f"Fetching {year}...", end=" ")
    try:
        resp = requests.get(BASE_URL, params={
            "year": year,
            "playoffs": 0,
            "min_minutes": 400,
            "select_fields": FIELDS,
        }, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # 筛选目标球员
        count = 0
        for row in data:
            nba_id = row.get("nba_id")
            if nba_id in TARGET_IDS:
                row["_target_name"] = TARGET_IDS[nba_id]
                all_data.append(row)
                count += 1

        print(f"{len(data)} players total, {count} targets found")
    except Exception as e:
        print(f"ERROR: {e}")

    time.sleep(0.5)

# 转为 DataFrame
df = pd.DataFrame(all_data)
df.to_csv("data/databallr_raw.csv", index=False)
print(f"\nTotal: {len(df)} player-seasons saved to data/databallr_raw.csv")
print(f"Players found: {df['player_name'].unique().tolist()}")
print(f"\nPer player:")
print(df.groupby("player_name")["year"].agg(["count", "min", "max"]))
