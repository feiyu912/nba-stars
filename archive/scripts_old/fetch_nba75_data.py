"""
批量拉取 75大+东契奇 共77名球员的 NBA API 逐赛季数据
"""
import json
import time
import pandas as pd
from nba_api.stats.endpoints import playercareerstats

with open("data/nba75_ids.json") as f:
    players = json.load(f)

print(f"Fetching career stats for {len(players)} players...")

all_rows = []
errors = []

for i, p in enumerate(players):
    name = p["name"]
    pid = p["nba_id"]
    print(f"  [{i+1:2d}/{len(players)}] {name} (id={pid})...", end=" ")

    try:
        career = playercareerstats.PlayerCareerStats(
            player_id=str(pid), per_mode36="PerGame"
        )
        df = career.get_data_frames()[0]

        for _, row in df.iterrows():
            all_rows.append({
                "player": name,
                "nba_id": pid,
                "season": row.get("SEASON_ID", ""),
                "team": row.get("TEAM_ABBREVIATION", ""),
                "age": row.get("PLAYER_AGE", None),
                "GP": row.get("GP", 0),
                "GS": row.get("GS", None),
                "MIN": row.get("MIN", 0),
                "PPG": row.get("PTS", 0),
                "RPG": row.get("REB", 0),
                "APG": row.get("AST", 0),
                "SPG": row.get("STL", None),
                "BPG": row.get("BLK", None),
                "TOV": row.get("TOV", None),
                "FGM": row.get("FGM", 0),
                "FGA": row.get("FGA", 0),
                "FG_PCT": row.get("FG_PCT", 0),
                "FG3M": row.get("FG3M", None),
                "FG3A": row.get("FG3A", None),
                "FG3_PCT": row.get("FG3_PCT", None),
                "FTM": row.get("FTM", 0),
                "FTA": row.get("FTA", 0),
                "FT_PCT": row.get("FT_PCT", 0),
            })
        print(f"{len(df)} seasons")
    except Exception as e:
        print(f"ERROR: {e}")
        errors.append(name)

    time.sleep(0.6)

result = pd.DataFrame(all_rows)

# 计算 TS%
result["TS_pct"] = result["PPG"] / (2 * (result["FGA"] + 0.44 * result["FTA"]))
result["TS_pct"] = result["TS_pct"].round(4)

result.to_csv("data/nba75_career_all.csv", index=False)

print(f"\nTotal: {len(result)} player-seasons")
print(f"Players: {result['player'].nunique()}")
print(f"Errors: {errors}")

# 汇总
summary = result.groupby("player").agg({
    "PPG": "mean", "RPG": "mean", "APG": "mean",
    "TS_pct": "mean", "GP": "sum",
    "season": ["min", "max", "count"],
}).round(3)
summary.columns = ["PPG", "RPG", "APG", "TS_pct", "GP",
                    "first_season", "last_season", "num_seasons"]
summary = summary.sort_values("PPG", ascending=False)
print(f"\nTop 20 by PPG:")
print(summary.head(20).to_string())
