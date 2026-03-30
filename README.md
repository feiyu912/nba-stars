# NBA Historical Player Ranking System

101 NBA players across 7 decades. Two independent rankings. All era-adjusted. Let data speak.

## Quick Start

```bash
pip install pandas scikit-learn nba_api requests streamlit altair matplotlib seaborn

# Launch interactive dashboard
streamlit run app.py

# Run ranking model
python notebooks/05_consensus_ranking.py
```

## Dashboard

`streamlit run app.py` then visit http://localhost:8501

| View | What it shows |
|------|--------------|
| **Scoring Ranking** | Pure scoring ability: who puts the ball in the basket best |
| **Impact Ranking** | Total offensive contribution: scoring + assists + gravity |
| **Head-to-Head** | Compare the two rankings to classify player types |
| **Scoring Breakdown** | Where points come from: 2P / 3P / FT structure |
| **Playoff Performance** | Who steps up in the playoffs vs regular season |
| **Player Lookup** | Deep dive into any player with ranking explanation |

## Results

### Scoring Ability (who scores the most, most efficiently)

| Rank | Player | PPG | Key Factor |
|:----:|--------|:---:|------------|
| 1 | Michael Jordan | 29.5 | Dominated a low-scoring era + playoff PPG 34.1 |
| 2 | Kevin Durant | 27.2 | Elite efficiency (TS% .632) + playoff riser |
| 3 | LeBron James | 26.7 | Volume + efficiency + 292 playoff games |
| 4 | Luka Doncic | 29.1 | Highest raw PPG among active, limited playoff sample |
| 5 | Stephen Curry | 24.5 | Best efficiency (TS% .621) + lowest FT reliance (16%) |
| 6 | Giannis | 24.7 | Elite per-minute scoring |
| 7 | George Gervin | 26.2 | Dominated 70s-80s scoring |
| 7 | Joel Embiid | 27.1 | High PPG but penalized for FT reliance (30%) |
| 9 | Kobe Bryant | 24.2 | 220 playoff games, scores more in playoffs |
| 10 | James Harden | 23.8 | High efficiency but FT-dependent (29%) |

### Offensive Impact (total contribution including assists and playmaking)

| Rank | Player | PPG | APG | Key Factor |
|:----:|--------|:---:|:---:|------------|
| 1 | Oscar Robertson | 25.5 | 9.4 | 1960s scoring + assists dominance (era Z-score) |
| 2 | Magic Johnson | 19.4 | 10.9 | All-time playmaker |
| 3 | LeBron James | 26.7 | 7.4 | Elite at both scoring and creating |
| 4 | Jerry West | 26.7 | 6.7 | Dominated across eras |
| 5 | Luka Doncic | 29.1 | 8.1 | Modern scoring + playmaking combo |
| 6 | James Harden | 23.8 | 8.0 | Volume scoring + elite assists |
| 7 | Nikola Jokic | 22.5 | 7.6 | Best passing big man ever |
| 8 | Michael Jordan | 29.5 | 5.1 | Scoring dominance lifts overall impact |
| 9 | Wilt Chamberlain | 30.6 | 4.3 | Historical statistical dominance |
| 10 | Stephen Curry | 24.5 | 6.2 | Gravity + efficiency revolution |

### Player Types (comparing both tables)

| Type | Description | Examples |
|------|-------------|---------|
| **Balanced** | Both rankings close | Jordan, Curry, LeBron, Doncic |
| **Pure Scorer** | Scoring >> Impact | Kobe, Carmelo, Shaq, Wilkins, Gervin |
| **Playmaker** | Impact >> Scoring | Nash, Stockton, Jokic, Magic |

## Key Findings

1. **Scoring scarcity matters** - Jordan's 29.6 PPG in 1997 (league avg 16.8) is more dominant than Doncic's 30.1 in 2025 (league avg 22.4)
2. **Playoffs separate the great** - Jordan +4.6, Jokic +5.4 in playoffs; Chamberlain -5.9, Dantley -3.6
3. **FT reliance varies wildly** - Klay Thompson 91% from field goals vs Dolph Schayes only 64%
4. **Scoring and impact are different things** - Shaq is #11 scorer but #38 impact; Nash is #77 scorer but #20 impact
5. **Sensitivity analysis confirms stability** - FT coefficient 0.6-0.8: TOP 10 shifts max 2 positions

## How It Works

### Scoring Ranking

```
Scoring Index = PPG (FT x 0.7) x TS+ (relative efficiency)

Era adjustments applied to each season:
  Pace:        PPG x (97 / era_pace)
  Competition: x sqrt(teams / 30)
  Scarcity:    x (1 + PPG_zscore x 0.1)

Playoff weight: each playoff game = 3x regular season game
Final = median of two sub-views (per-game + per-minute era-adjusted)
```

### Impact Ranking

```
Ridge regression: era-adjusted Z-scores -> predict O-DPM

Training: 53 modern players with actual O-DPM data
Features: PPG_z, TS%_z, APG_z, peak_PPG_z (all relative to contemporaries)
Applied to: all 101 players

Note: O-DPM is a proxy target, not ground truth
```

### Corrections

| Correction | Method | Effect |
|-----------|--------|--------|
| FT Penalty | FT points x 0.7 | Curry (16% FT) rises, Embiid (30%) drops |
| Pace | PPG x (97/pace) | 1960s pace=125 discounted, modern ~unchanged |
| Competition | sqrt(teams/30) | 8-team era = 0.52x, 30-team era = 1.0x |
| Scarcity | 1 + Z-score x 0.1 | Low-scoring eras (90s-00s) get bonus |

## Data

| Source | Coverage | Content |
|--------|----------|---------|
| NBA API | 1959-2026 | 101 players: 1541 regular + 1091 playoff seasons |
| databallr API | 2001-2026 | 53 players x 641 seasons, 388 metrics (O-DPM, On-Off, rTS%) |

## Player Pool

**NBA 75th Anniversary Team** (76 players) + **25 additional** (Jokic, Embiid, SGA, Tatum, Edwards, Booker, Morant, Mitchell, Irving, Butler, Doncic, T-Mac, Yao, Dwight, Vince Carter, PG13, Klay, Tony Parker, Pau Gasol, Bosh, Draymond, Ginobili, English, Bernard King, Dantley)

## Project Structure

```
nba-stars/
├── app.py                          # Streamlit Dashboard (6 views)
├── data/
│   ├── nba100_career_all.csv       # Regular season (NBA API)
│   ├── nba100_playoffs.csv         # Playoffs (NBA API)
│   ├── nba100_databallr.csv        # Advanced metrics (databallr)
│   └── nba100_ids.json             # Player ID mapping
├── notebooks/
│   ├── 05_consensus_ranking.py     # Main model: scoring + impact
│   ├── 06_scoring_breakdown.py     # Structure analysis + DPM comparison
│   └── 07_visualization.py         # Static charts
├── results/
│   ├── scoring_ranking.csv         # Scoring ability ranking
│   ├── impact_ranking.csv          # Offensive impact ranking
│   └── scoring_analysis.png        # Charts
├── fetch_databallr_100.py          # Data fetching scripts
├── fetch_finals.py
└── archive/                        # Exploration history
```

## Methodology Evolution

1. Manual weights -> too subjective
2. Ridge on O-DPM -> assists over-weighted
3. Ridge on PtsCreated -> same problem
4. **Solution: separate scoring and impact into independent rankings**
5. Added: FT penalty, pace/competition/scarcity correction, playoff weighting
6. Validated: sensitivity analysis (stable), DPM comparison (r=0.555, explainable)
7. Era Z-score adjustment applied to both rankings

## Quality Assurance

- **Sensitivity Analysis**: FT coefficient 0.6-0.8, TOP 10 max shift = 2 positions
- **Explanation Layer**: Every TOP 20 player has factor-by-factor breakdown
- **DPM Comparison**: r=0.555 correlation with professional metric, differences explainable
- **Known Limitations**: O-DPM is proxy; modern players have richer data; FT 0.7 has subjective element

## Future Work

| Dimension | Status |
|-----------|--------|
| Defense | D-DPM data ready, not yet modeled |
| Legacy / Awards | MVP, championships, All-NBA - not started |
| Composite GOAT Ranking | Multi-dimension aggregate - not started |

## Tech Stack

Python 3.12 | pandas | scikit-learn | nba_api | Streamlit | Altair | Matplotlib
