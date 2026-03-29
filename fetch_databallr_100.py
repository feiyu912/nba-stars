"""
从 databallr API 获取 2001-2026 全联盟数据，筛选 101 名目标球员
包含核心指标 + 防守难度调整指标
"""
import json
import time
import requests
import pandas as pd

with open("data/nba100_ids.json") as f:
    TARGET_IDS = {int(k): v for k, v in json.load(f).items()}

print(f"Target players: {len(TARGET_IDS)}")

BASE_URL = "https://api.databallr.com/api/supabase/player_stats_with_metrics"

# 第一批：核心指标 (8个字段限制)
FIELDS_1 = ",".join([
    "player_name", "nba_id", "TeamAbbreviation", "Minutes", "Pos2",
    "year", "playoffs", "GamesPlayed",
])

FIELDS_2 = ",".join([
    "player_name", "nba_id", "year", "playoffs",
    "d_Points_PerGame", "d_Points_Per100",
    "TS_pct", "rTSPct",
])

FIELDS_3 = ",".join([
    "player_name", "nba_id", "year", "playoffs",
    "d_Points_Created_PerGame", "d_Points_Created_Per100",
    "dpm", "o_dpm",
])

FIELDS_4 = ",".join([
    "player_name", "nba_id", "year", "playoffs",
    "d_Assists_PerGame", "d_Assists_Per100",
    "netrtg_on_off", "d_dpm",
])

FIELDS_5 = ",".join([
    "player_name", "nba_id", "year", "playoffs",
    "playtype_diff", "pt_adj_rTS",
    "SFC_pct", "PASSING_on-ball-time%",
])

all_batches = {
    "batch1": FIELDS_1,
    "batch2": FIELDS_2,
    "batch3": FIELDS_3,
    "batch4": FIELDS_4,
    "batch5": FIELDS_5,
}

all_data = {}  # key = (nba_id, year) → merged dict

for batch_name, fields in all_batches.items():
    print(f"\n=== {batch_name} ===")
    for year in range(2001, 2027):
        print(f"  {year}...", end=" ")
        try:
            resp = requests.get(BASE_URL, params={
                "year": year, "playoffs": 0, "min_minutes": 400,
                "select_fields": fields,
            }, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            count = 0
            for row in data:
                nba_id = row.get("nba_id")
                if nba_id in TARGET_IDS:
                    key = (nba_id, year)
                    if key not in all_data:
                        all_data[key] = {"nba_id": nba_id, "year": year,
                                         "player_name": TARGET_IDS[nba_id]}
                    all_data[key].update(row)
                    count += 1

            print(f"{count} targets", end="")
        except Exception as e:
            print(f"ERR:{e}", end="")
        time.sleep(0.3)
    print()

# 转 DataFrame
df = pd.DataFrame(all_data.values())
df.to_csv("data/nba100_databallr.csv", index=False)

print(f"\nTotal: {len(df)} player-seasons")
print(f"Players found: {df['player_name'].nunique()}")
print(f"\nPer player season count:")
counts = df.groupby("player_name")["year"].count().sort_values(ascending=False)
print(counts.to_string())
