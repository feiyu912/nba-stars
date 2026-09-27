# NBA Historical Player Ranking System

[![CI](https://github.com/feiyu912/nba-stars/actions/workflows/ci.yml/badge.svg)](https://github.com/feiyu912/nba-stars/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Data verified](https://img.shields.io/badge/data%20verified-100%25%20vs%20NBA.com-2fd39a)](scripts/verify_against_nba_api.py)
[![Live dashboard](https://img.shields.io/badge/live%20dashboard-feiyu912.github.io%2Fnba--stars-35bdf0)](https://feiyu912.github.io/nba-stars/)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)

101 NBA players across 8 decades. Five independent, era-adjusted rankings, **every row verified against the primary source**. Let data speak.

**[→ Browse the dashboard](https://feiyu912.github.io/nba-stars/)** — a static, bilingual (EN/中文) site generated from the same result files. A Streamlit app with the same views runs locally (`make app`).

## Quick Start

```bash
pip install -r requirements.txt          # 依赖已锁定版本
python -m nbastars.run                   # 按正确顺序跑完所有维度, 写出 results/
streamlit run app.py                     # 仪表盘: http://localhost:8501
```

其他命令 (见 `Makefile`):

```bash
make test        # 测试套件: 数据契约 / 排名引擎 / 指标构造 / 界面文案
make verify      # 常规赛数据校验 (对照 Basketball-Reference, 需先下载参考数据)
make lint        # ruff
```

> 单独跑某个维度: `python -m nbastars.run --only playmaking`
> 旧的 `notebooks/05..10*.py` 仍可用, 现在只是薄壳 — 计算逻辑全在 `nbastars/` 包里。

## Dashboard

The dashboard is bilingual (English / 中文) — switch at the top of the sidebar. Once a language
is selected no text from the other language appears (the only exceptions are the switcher itself
and player names; enforced by tests).

Views are grouped by dimension, and each dimension offers the sub-views its data actually supports:

| Category | Views |
|----------|-------|
| 🏀 Offense | Scoring Ranking · Scoring Breakdown (2P/3P/FT) · Offensive Impact · Playmaking |
| 🛡️ Defense | Defense Ranking · **Steals & Blocks** (two skills, ranked separately) · **Defensive Impact** (D-DPM) |
| 📊 Rebounding | Rebounding Ranking · **Off / Def Rebounds** (separately ranked) |
| 🔀 Cross-dimension | Playoff Performance (scoring / rebounds / assists) · Head-to-Head |
| 🔎 Player Lookup | Full profile with factor-by-factor explanation |

The split views exist because combining steals with blocks, or offensive with defensive rebounds,
lets two different skills cancel each other out. Defense has fewer views than offense for a real
reason, not an organisational one: the NBA has never recorded steals/blocks in the playoffs, so
there is no playoff defense view to build.

## Results

### Scoring Ability

`Scoring Index = PPG (FT discounted 0.7x, pace-adjusted) × TS+ × scarcity`, combined with a
per-minute view; each playoff game counts 3x a regular-season game.

| Rank | Player | Career PPG | TS% | Playoff PPG | FT share of scoring |
|:----:|--------|:----------:|:---:|:-----------:|:-------------------:|
| 1 | Michael Jordan | 29.5 | .559 | 34.1 | 23% |
| 2 | Kevin Durant | 27.1 | .626 | 28.6 | 23% |
| 3 | Luka Doncic | 29.3 | .589 | 31.5 | 22% |
| 4 | LeBron James | 26.7 | .592 | 27.9 | 20% |
| 5 | Stephen Curry | 24.5 | .621 | 26.2 | 16% |
| 6 | Giannis Antetokounmpo | 24.7 | .607 | 25.8 | 24% |
| 7 | George Gervin | 26.2 | .571 | 24.9 | 22% |
| 8 | Joel Embiid | 27.1 | .608 | 25.5 | 30% |
| 9 | Shaquille O'Neal | 23.0 | .588 | 22.3 | 21% |
| 9 | Kobe Bryant | 24.2 | .543 | 24.9 | 25% |

### Offensive Impact (ridge regression on O-DPM)

| Rank | Player | Career PPG | Career APG | Actual O-DPM | Predicted |
|:----:|--------|:----------:|:----------:|:------------:|:---------:|
| 1 | Oscar Robertson | 25.5 | 9.4 | — | 5.76 |
| 2 | Magic Johnson | 19.4 | 10.9 | — | 5.02 |
| 3 | LeBron James | 26.7 | 7.4 | 5.29 | 4.74 |
| 4 | Jerry West | 26.7 | 6.7 | — | 4.66 |
| 5 | Luka Doncic | 29.3 | 8.2 | 4.45 | 4.52 |
| 6 | James Harden | 23.9 | 7.4 | 4.64 | 4.27 |
| 7 | Nikola Jokic | 22.4 | 7.6 | 3.89 | 4.21 |
| 8 | Michael Jordan | 29.5 | 5.1 | 3.09 | 4.10 |
| 9 | Wilt Chamberlain | 30.1 | 4.4 | — | 4.09 |
| 10 | Stephen Curry | 24.5 | 6.2 | 4.52 | 4.08 |

*"—" = no O-DPM available (the model extrapolates for pre-2001 players).*

### Other dimensions (top 5)

| Dimension | #1 | #2 | #3 | #4 | #5 |
|-----------|----|----|----|----|----|
| Playmaking | John Stockton | Magic Johnson | Chris Paul | Steve Nash | Jason Kidd |
| Defense | Hakeem Olajuwon | David Robinson | Kareem Abdul-Jabbar | Anthony Davis | Patrick Ewing |
| Rebounding | Dennis Rodman | Wilt Chamberlain | Dwight Howard | Bill Russell | Moses Malone |

### Rank quality

Ranks are competition ranks (`method="min"`): ties are real ties, and the next rank skips.
Ranked players per dimension: scoring 101, impact 101, playmaking 101, **defense 82**,
rebounding 101. Defense is short of 101 because 19 players are excluded, under two rules:

| Rule | Players | Why |
|------|---------|-----|
| No steals/blocks at all | 11 | careers entirely before 1973-74, when the NBA started recording them |
| Fewer than 5 seasons of it | 8 | the peak window is 5 seasons; with 1-4 seasons the "peak" is just an average of those seasons (Jerry West's would be a single 31-game season) |

The steals and blocks sub-rankings apply the same two rules, so they also list 82 players.
Unique rank values: scoring 85, impact 101, playmaking 80, defense 67, rebounding 81 — the
ties come from the median-of-two-views step, which collapses players whose two view ranks
sum to the same value.

## How It Works

Every dimension follows the same skeleton (`nbastars/engine.py`):

```
1. Two views per dimension (bulk vs per-minute), each era-adjusted
2. Per view: 0.6 × peak-5 seasons + 0.4 × career average
3. Playoff handling:
     scoring / playmaking  → mix regular + playoff by weighted games (playoff game = 3x)
     defense / rebounding  → regular-season stats × playoff experience bonus
       (SPG/BPG/OREB have no playoff splits, so this is a workaround, not an equivalent)
4. Each view ranked independently, then median rank → final rank
```

Era adjustments (`nbastars/era.py`):

| Adjustment | Method | Effect |
|-----------|--------|--------|
| Pace | per-game × (97 / era pace) | 1960s (pace≈125) discounted, modern ~unchanged |
| Competition | × sqrt(teams / 30) | 8-team era = 0.52x, 30-team era = 1.0x |
| Scarcity | × 1 + (same-year Z-score) × 0.1 | dominating a low-scoring era earns a bonus |
| Era Z-score | same-year Z-score of PPG / APG / TS% / SPG / BPG | input to the ridge models |

## Data

| Source | Coverage | Content |
|--------|----------|---------|
| NBA.com stats API | 1948-2026 | 101 players: regular season + playoffs — **single source for everything** |
| databallr API | 2001-2026 | 56 players: O-DPM / D-DPM targets for the ridge models |

**Data provenance note:** the 2025-26 season was originally patched from Basketball-Reference
(regular season) and ESPN (playoffs) because the local snapshot had been taken in late April 2026,
mid-season. A fresh primary-source fetch later confirmed the Basketball-Reference values were
identical and the ESPN values differed only by 0.1-0.2 minutes on 5 rows; those rows have since
been replaced with the official values, so **the whole dataset is now single-source**.

### Fetching data on this machine

`stats.nba.com` is only reachable from a page already loaded on `nba.com` — direct requests,
curl and python all fail (the API requires `Referer` / `x-nba-stats` headers that only a
browser page context supplies). The working route is:

```bash
python scripts/browser_collector.py --out /tmp/nba_fetch --port 8899      # 终端 1
# 打开 https://www.nba.com/stats/players/traditional, 控制台里跑 scripts/browser_fetch_snippet.js
python scripts/verify_against_nba_api.py --fetch-dir /tmp/nba_fetch      # 校验
```

### Verification

Two independent cross-checks against sources that are *not* NBA.com:

```bash
python scripts/verify_reference_data.py --ref-dir /tmp/nba_verify   # 常规赛 vs Basketball-Reference
python scripts/verify_playoffs_espn.py  --cache /tmp/nba_verify/hoopr  # 季后赛 vs ESPN
```

| Check | Scope | Result |
|-------|-------|--------|
| **Primary source** (`scripts/verify_against_nba_api.py`) | 1,459 regular + 1,102 playoff player-seasons × 9 fields | **100% identical, 0 differences** |
| Regular season per-game stats | 1,459 player-seasons × 9 fields | **1,457/1,459 = 99.86%** agree |
| Multi-team season structure | 41 seasons, TOT row vs team rows | GP sums match exactly, no structural anomalies |
| Rebounds file | 1,459 player-seasons | agrees with the reference; same 2 early-era diffs |
| Playoffs | 468 player-seasons (2002+) | 0 field mismatches attributable to this dataset |

The 3 remaining regular-season differences are **known NBA.com ↔ Basketball-Reference
disagreements in early data**, not ingestion bugs:

| Player | Season | Field | NBA.com | B-R |
|--------|--------|-------|---------|-----|
| Bill Sharman | 1950-51 | RPG | 3.1 | 3.5 |
| Bill Sharman | 1950-51 | FGA | 11.6 | 12.3 |
| Jerry West | 1963-64 | RPG | 6.2 | 6.0 |

They are left as-is: changing them would make two seasons inconsistent with the primary source
without a third source to adjudicate. Playoff diffs outside this dataset's control are all
ESPN-side gaps (e.g. ESPN is missing one 2006 playoff game, so its GP reads 22 where the Heat
actually played 23; ESPN's `did_not_play` flag is unreliable and is not used).

### Known data gaps — nothing is imputed

**Missing means missing.** Earlier versions filled these gaps with medians or fixed ratios,
which produced ranks that looked real but were artifacts of the fill. That is now forbidden:
a player without the data shows **N/A** and is excluded from that dimension's ranking.

| Field | Missing until | Affected | How it's handled |
|-------|--------------|----------|------------------|
| MIN | 1951-52 | 8 player-seasons | excluded from per-minute views |
| REB | 1950-51 | 3 player-seasons | excluded from rebounding views |
| SPG / BPG | 1973-74 | 11 players' entire careers | **N/A, not ranked** in defense (`def_rank` is empty) |
| SPG / BPG (partial) | 1973-74 | 8 players have only 1-4 seasons | **N/A, not ranked** — too few seasons for a 5-year peak window |
| OREB / DREB split | 1973-74 | 11 players' entire careers | total rebounds still ranked; ORB/DRB shown as N/A |
| TOV | 1977-78 | 19 players' entire careers | AST/TOV shown as N/A; playmaking index flagged `TOV_imputed` |
| FG3M | 1979-80 | — | treated as 0 (no three-point line existed) |

The dashboard shows these exclusions on each affected view, and the page header carries a
standing notice about which fields did not exist in which era.

## Known Limitations

1. **Early-era players are not comparable to modern ones.** NBA began recording steals and
   blocks in 1973-74, turnovers in 1977-78, and the offensive/defensive rebound split in
   1973-74. Players whose careers ended before those dates simply have no data for those
   dimensions. They are excluded (not imputed) and the dashboard lists them explicitly.
2. **AST/TOV for pre-1977 players is still an estimate, and it matters a lot.** Turnovers
   were not recorded before 1977-78, so for 19 players the assist-to-turnover ratio is
   estimated from a league-average turnover count (2.5) and the whole playmaking index is
   multiplied by that estimate. The dashboard marks these players **Estimated**.
   This is the last remaining estimated input, and it is not a small effect: replacing it with
   a neutral multiplier moves **92 of 101 players**, up to 30 positions — Oscar Robertson
   falls from #6 to #36, Bob Cousy from #14 to #38. In other words his top-10 playmaking rank
   currently depends on an invented turnover number. Three consistent options are open:
   neutral 1.0 multiplier (penalises pre-1977 vs modern), no multiplier for anyone (the only
   era-consistent formula, but it drops AST/TOV from the index), or keep the estimate.
   Not changed unilaterally because it rewrites a headline ranking.
4. **Median-of-ranks creates ties.** Combining two views by median rank discards magnitude
   information; players whose two view ranks sum to the same value tie. An alternative is to
   average Z-scored view scores — not adopted here to keep results comparable with earlier runs.
5. **Proxy targets.** O-DPM / D-DPM come from a third party and are themselves estimates.
   Cross-validated R² below measures how well box scores reproduce *that metric*, not true impact.
6. **Z-scores are pool-relative.** Scarcity and era Z-scores compare a player to the other
   members of this 101-player pool, not to the whole league — the pool skews toward all-time
   greats, which compresses Z values.
7. **No ABA data.** Julius Erving's and Moses Malone's ABA seasons are deliberately excluded.
8. **Multi-team seasons take the combined row only.** Per-team splits are dropped, so the data
   cannot answer "how did he play for team X before the trade" — a deliberate trade-off.

## Model validation

Ridge models now report out-of-sample metrics (5-fold CV, scaler fit on training folds only):

| Model | Train rows | In-sample R² | CV R² | CV Spearman |
|-------|-----------|--------------|-------|-------------|
| Offensive impact → O-DPM | 53 | 0.472 | 0.416 | 0.687 |
| Defensive impact → D-DPM | 53 | 0.522 | 0.359 | 0.667 |

The previous README quoted `r=0.555`; that was an in-sample correlation. The cross-validated
Spearman of 0.687 is the number to cite.

## Project structure

```
nbastars/                    # 计算核心 (唯一实现处)
├── config.py                # 时代基准表、权重、阈值、路径
├── data.py                  # 加载 + 数据契约校验 (重复赛季/GP>82 直接报错)
├── era.py                   # pace / 竞争强度 / 稀缺性 / 时代 Z-score
├── engine.py                # 排名引擎: 双视角 → 巅峰+生涯 → 季后赛 → 中位数名次
├── dimensions.py            # 五个维度的指标构造
├── ridge.py                 # 岭回归 + 交叉验证
├── i18n.py                  # 界面文案的中英文对照 (两种语言键必须一一对应)
├── dashboard_data.py        # 仪表盘的数据装配 (单独抽出以便测试)
└── run.py                   # 按正确顺序跑完并写出 results/

docs/                        # 静态站 (GitHub Pages 直接托管这个目录)
├── index.html
└── assets/{style.css,app.js,data.js,fonts/}

.github/workflows/ci.yml     # lint + 测试 + 校验站点数据是否为最新

scripts/
├── verify_reference_data.py # 常规赛校验 (对照 Basketball-Reference)
├── verify_playoffs_espn.py  # 季后赛校验 + 当季补齐数据源 (对照 ESPN)
└── repair_dataset.py        # 数据修复: 多队赛季去重 + 当季补齐

notebooks/                   # 薄壳: 跑维度 + 打印分析报告
tests/                       # 测试: 数据契约 / 引擎 / 指标构造 / 界面文案
data/                        # 原始数据 + 101 人 ID 映射
results/                     # 各维度排名 + all_rankings.csv (仪表盘读这一份)
app.py                       # Streamlit 仪表盘
archive/                     # 探索历史 (不参与运行)
```

## Methodology evolution

1. Manual weights → too subjective
2. Ridge on O-DPM → assists over-weighted
3. Ridge on PtsCreated → same problem
4. **Solution: separate scoring and impact into independent rankings**
5. Added FT discount, pace/competition/scarcity correction, playoff weighting
6. Split playmaking / defense / rebounding into their own dimensions
7. **Data correctness pass** (see below) + out-of-sample validation + shared engine

### Fixed in the correctness pass

| Issue | Impact | Fix |
|-------|--------|-----|
| Multi-team seasons stored as 3 rows (team A + team B + TOT) | 30 players / 41 seasons triple-counted: peak-5 window double-counted, GP summed past 82, era Z-score cohorts polluted | keep only the TOT row (`scripts/repair_dataset.py`), now enforced by a data contract test |
| `rank().astype(int)` truncated half-ranks | 101 players collapsed to 76-82 unique ranks — fake ties | rank the untruncated median (`engine.final_rank`) |
| `era_group` derived from data availability | Michael Jordan labelled "Modern (2001+)" | labelled by median career season; availability moved to its own flag |
| Scaler fit on all rows before the train split | leakage into standardisation | fit on training folds only |
| 2025-26 season incomplete | last 6-8 games missing per active player, playoffs absent entirely | patched from B-R / ESPN |
| Dead code and duplicated outputs | `scoring_ranking.csv` and `impact_ranking.csv` were byte-identical copies of one 50-column frame | each dimension writes only its own columns; `all_rankings.csv` added |
| Four copies of the era table / summarise logic | adding a dimension meant copying 220 lines | one engine + per-dimension config |
| Median-fill / 30-70 ratio for missing stats | 11 pre-1973 players got defense ranks built from fabricated values; Jerry West's real single season then had to compete against them | **no imputation at all** — N/A and excluded from that dimension, flagged in the UI |

## Future work

| Dimension | Status |
|-----------|--------|
| Defense (full) | STL/BLK proxy in place; D-DPM model exists; no all-defense team data |
| Legacy / Awards | `fetch_finals.py` exists but is **not wired in** and its round-detection is only valid from 1968 |
| Composite GOAT ranking | Not started — deliberately last |
| League-wide Z-scores | Requires league-level data instead of the 101-player pool |
| More independent sources | Pre-2002 playoff verification is still missing |

## Tech stack

Python 3.10+ | pandas 3 | scikit-learn | scipy | Streamlit | Altair | nba_api | pytest | ruff