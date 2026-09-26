"""获取 101 名球员的总决赛数据。

⚠️ 这个脚本目前没有接入主流程 (nbastars.run), 产物 data/nba100_finals_*.csv
也还没有被任何排名维度消费。保留它是为了 ROADMAP 里的 "Legacy / Awards" 维度。

已知的方法论问题 (使用前必须解决):
  用"季后赛打过 4 个不同对手"来判断是否进了总决赛, 只对 1968 年之后的赛制成立。
  1968 年之前季后赛轮次更少 (1950 年代只有分区决赛+总决赛),
  1975-76 赛季也只有 3 轮 —— 这些年份会被漏判。

用法: python fetch_finals.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"

# 从 1968 年起季后赛固定 4 轮 (1975-76 例外, 只有 3 轮)
FOUR_ROUND_SEASONS = {y for y in range(1968, 2026)} - {1975}


def main() -> int:
    try:
        from nba_api.stats.endpoints import playergamelog
    except ImportError:
        print("需要 nba_api: pip install nba_api")
        return 2

    players = {
        int(k): v for k, v in pd.read_json(DATA_DIR / "nba100_ids.json", typ="series").items()
    }
    po = pd.read_csv(DATA_DIR / "nba100_playoffs.csv")

    all_rows: list[dict] = []
    errors: list[tuple[str, str]] = []
    skipped_era: set[int] = set()

    for i, (pid, name) in enumerate(players.items(), 1):
        player_po = po[po["nba_id"] == pid]
        if player_po.empty:
            continue
        seasons = sorted(player_po["season"].str[:4].unique())
        print(f"[{i:3d}/{len(players)}] {name}: {len(seasons)} 个季后赛赛季", end=" ")

        found = 0
        for season in seasons:
            if int(season) not in FOUR_ROUND_SEASONS:
                skipped_era.add(int(season))
                continue
            try:
                log = playergamelog.PlayerGameLog(
                    player_id=str(pid), season=str(season), season_type_all_star="Playoffs"
                )
                df = log.get_data_frames()[0]
                if df.empty:
                    continue
                # nba_api 返回的比赛按时间倒序, 第一行是最后一场
                last_opponent = df.iloc[0]["MATCHUP"].split()[-1]
                opponents = df["MATCHUP"].str.split().str[-1].unique()
                if len(opponents) < 4:
                    continue
                finals_games = df[df["MATCHUP"].str.contains(last_opponent, regex=False)]
                for _, row in finals_games.iterrows():
                    all_rows.append({
                        "player": name, "nba_id": pid,
                        "season": f"{season}-{str(int(season) + 1)[2:]}",
                        "opponent": last_opponent,
                        "PPG": row["PTS"], "RPG": row["REB"], "APG": row["AST"],
                        "MIN": row["MIN"], "FGM": row["FGM"], "FGA": row["FGA"],
                        "FTM": row["FTM"], "FTA": row["FTA"],
                    })
                found += 1
            except Exception as exc:  # 不静默吞错: 记录球员+赛季+原因
                errors.append((f"{name} {season}", f"{type(exc).__name__}: {exc}"))
            time.sleep(0.3)
        print(f"-> {found} 次总决赛")

    if skipped_era:
        print(f"\n跳过 {len(skipped_era)} 个赛季 (1968 年前的轮次赛制无法用对手数判断): "
              f"{min(skipped_era)}-{max(skipped_era)}")

    if not all_rows:
        print("没有抓到任何总决赛数据")
        return 1

    result = pd.DataFrame(all_rows)
    result["TS_pct"] = (
        result["PPG"] / (2 * (result["FGA"] + 0.44 * result["FTA"]))
    ).round(4)
    result.to_csv(DATA_DIR / "nba100_finals_games.csv", index=False)

    avg = result.groupby("player").agg(
        finals_PPG=("PPG", "mean"), finals_TS=("TS_pct", "mean"), finals_games=("season", "count")
    ).round(3).reset_index()
    appearances = result.groupby("player")["season"].nunique().reset_index()
    appearances.columns = ["player", "finals_appearances"]
    avg = avg.merge(appearances, on="player").sort_values("finals_PPG", ascending=False)
    avg.to_csv(DATA_DIR / "nba100_finals_avg.csv", index=False)

    print(f"\n总决赛 {len(result)} 场 / {result['player'].nunique()} 人")
    print("-> data/nba100_finals_games.csv, data/nba100_finals_avg.csv")
    print("\n总决赛场均得分前 15:")
    print(avg.head(15).to_string(index=False))

    if errors:
        print(f"\n失败 {len(errors)} 次 (未计入结果):")
        for who, why in errors[:15]:
            print(f"  {who}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
