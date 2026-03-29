"""
获取101名球员的总决赛数据
方法: 拉每个赛季的季后赛gamelog, 最后一轮对手=总决赛
"""
import json, time, pandas as pd
from nba_api.stats.endpoints import playergamelog

with open("data/nba100_ids.json") as f:
    players = {int(k): v for k, v in json.load(f).items()}

# 先从季后赛数据确认每个球员打了哪些赛季的季后赛
po = pd.read_csv("data/nba100_playoffs.csv")

all_finals = []
errors = []

for pid, name in players.items():
    player_po = po[po["nba_id"] == pid]
    if len(player_po) == 0:
        continue

    seasons = player_po["season"].str[:4].unique()
    print(f"{name}: checking {len(seasons)} playoff seasons...", end=" ")

    finals_count = 0
    for season in seasons:
        try:
            log = playergamelog.PlayerGameLog(
                player_id=str(pid), season=str(season),
                season_type_all_star='Playoffs'
            )
            df = log.get_data_frames()[0]
            if len(df) == 0:
                continue

            # 最后打的对手 = 最后一轮 = 如果打到总决赛就是总决赛对手
            # 但怎么判断是不是总决赛？看日期: 6月的比赛 = 总决赛(1985后)
            # 或者看总场次: 如果打了15+场说明至少到了分区决赛
            last_opp = df.iloc[0]["MATCHUP"].split()[-1]
            finals_games = df[df["MATCHUP"].str.contains(last_opp)]

            # 判断是否到了总决赛:
            # 方法: 如果这是第4轮对手 (打了4个不同对手)
            all_opps = df["MATCHUP"].str.split().str[-1].unique()

            if len(all_opps) >= 4:  # 打了4个对手 = 到了总决赛
                for _, row in finals_games.iterrows():
                    all_finals.append({
                        "player": name, "nba_id": pid,
                        "season": f"{season}-{int(season)+1}",
                        "opponent": last_opp,
                        "PPG": row["PTS"], "RPG": row["REB"],
                        "APG": row["AST"], "MIN": row["MIN"],
                        "FGM": row["FGM"], "FGA": row["FGA"],
                        "FTM": row["FTM"], "FTA": row["FTA"],
                    })
                finals_count += 1

        except Exception as e:
            pass

        time.sleep(0.3)

    print(f"{finals_count} Finals appearances")

result = pd.DataFrame(all_finals)
if len(result) > 0:
    result["TS_pct"] = result["PPG"] / (2 * (result["FGA"] + 0.44 * result["FTA"]))

    # 汇总
    finals_avg = result.groupby("player").agg({
        "PPG": "mean", "TS_pct": "mean",
        "season": "count",  # 总决赛场次
    }).round(2).reset_index()
    finals_avg.columns = ["player", "finals_PPG", "finals_TS", "finals_games"]

    # 总决赛次数 (不同赛季)
    finals_appearances = result.groupby("player")["season"].nunique().reset_index()
    finals_appearances.columns = ["player", "finals_appearances"]
    finals_avg = finals_avg.merge(finals_appearances, on="player")

    result.to_csv("data/nba100_finals_games.csv", index=False)
    finals_avg.to_csv("data/nba100_finals_avg.csv", index=False)

    print(f"\nTotal: {len(result)} Finals games, {result['player'].nunique()} players")
    print(f"\nTop 20 Finals scorers:")
    print(finals_avg.sort_values("finals_PPG", ascending=False).head(20).to_string(index=False))
else:
    print("No Finals data found!")
