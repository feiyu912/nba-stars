"""
从 NBA API 获取10名球员的真实生涯数据
数据源: nba_api (stats.nba.com 官方接口)
"""
import time
import pandas as pd
from nba_api.stats.endpoints import playercareerstats

# 球员ID映射 (来自 nba_api.stats.static.players)
PLAYERS = {
    "Michael Jordan": 893,
    "LeBron James": 2544,
    "Stephen Curry": 201939,
    "Kevin Durant": 201142,
    "Shaquille O'Neal": 406,
    "Kareem Abdul-Jabbar": 76003,
    "Wilt Chamberlain": 76375,
    "Kobe Bryant": 977,
    "James Harden": 201935,
    "Luka Doncic": 1629029,
}

all_rows = []

for name, pid in PLAYERS.items():
    print(f"Fetching {name} (id={pid})...")
    try:
        career = playercareerstats.PlayerCareerStats(
            player_id=str(pid),
            per_mode36="PerGame"
        )
        df = career.get_data_frames()[0]  # Regular season per game
        # 取全部赛季数据
        for _, row in df.iterrows():
            all_rows.append({
                "player": name,
                "season": row.get("SEASON_ID", ""),
                "team": row.get("TEAM_ABBREVIATION", ""),
                "GP": row.get("GP", 0),
                "MIN": row.get("MIN", 0),
                "PPG": row.get("PTS", 0),
                "RPG": row.get("REB", 0),
                "APG": row.get("AST", 0),
                "FG_PCT": row.get("FG_PCT", 0),
                "FG3_PCT": row.get("FG3_PCT", 0),
                "FT_PCT": row.get("FT_PCT", 0),
                "FGA": row.get("FGA", 0),
                "FTA": row.get("FTA", 0),
                "FG3A": row.get("FG3A", 0),
            })
        print(f"  -> {len(df)} seasons found")
    except Exception as e:
        print(f"  -> ERROR: {e}")
    time.sleep(1)  # 避免被限流

result = pd.DataFrame(all_rows)

# 计算 TS%（真实命中率）
# TS% = PTS / (2 * (FGA + 0.44 * FTA))
result["TS_pct"] = result["PPG"] / (2 * (result["FGA"] + 0.44 * result["FTA"]))
result["TS_pct"] = result["TS_pct"].round(4)

result.to_csv("data/nba_career_stats_real.csv", index=False)
print(f"\nTotal: {len(result)} player-seasons saved to data/nba_career_stats_real.csv")
print("\nSample:")
print(result.groupby("player")[["PPG", "TS_pct", "APG", "GP"]].mean().round(3))
