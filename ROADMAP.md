# Roadmap: NBA Player Analysis System

## Core Philosophy

- Each dimension is an independent ranking with its own methodology
- Same rigor as Scoring: era-adjusted, data-driven, sensitivity-tested
- Composite ranking comes LAST, after all dimensions are solid

## System Structure

```
NBA Player Analysis System
│
├── Offense
│   ├── Scoring (得分能力)              ✅ Done
│   ├── Offensive Impact (进攻影响力)    ✅ Done
│   └── Playmaking (组织能力)           🔄 Next
│
├── Defense
│   ├── Overall Defensive Impact        ⬜ Planned
│   ├── Rim Protection                  ⬜ Planned
│   └── Perimeter Defense               ⬜ Planned
│
├── Rebounding
│   ├── Offensive Rebounds              ⬜ Planned (need to re-fetch OREB/DREB)
│   └── Defensive Rebounds              ⬜ Planned
│
├── Basketball IQ
│   ├── Shot Selection (TS vs USG)      ⬜ Planned
│   ├── Turnover Rate                   ⬜ Planned
│   └── Clutch / Playoff Performance    ⬜ Planned
│
├── Position Rankings                   ⬜ Planned
│   ├── Guards / Wings / Bigs
│   └── Within-position comparison
│
└── Composite GOAT Ranking              ⬜ Last
    └── Multi-dimension aggregate
```

## Methodology Principles (applied to every dimension)

1. **Era adjustment** - Z-score against contemporaries, not raw values
2. **Playoff weighting** - Big games matter more (3x multiplier)
3. **Scarcity bonus** - Dominating in a tough era counts extra
4. **Two-layer model** - All 101 players (basic data) + 53 modern (advanced data)
5. **Sensitivity analysis** - Test key parameters for stability
6. **Explanation layer** - Every ranking has factor-by-factor breakdown

## Data Needs

| Dimension | NBA API (have) | databallr (have) | Need to fetch |
|-----------|---------------|-----------------|---------------|
| Playmaking | APG, TOV | PtsCreated, Assists/100, on-ball-time% | AST% from stat-nba |
| Defense | SPG, BPG | D-DPM | DWS from stat-nba |
| Rebounding | RPG | - | OREB/DREB (re-fetch from NBA API) |
| Basketball IQ | FGA, TOV, TS% | playtype_diff, pt_adj_rTS | - |

## Bonus Ideas
- [ ] Offensive style classification (3pt / mid-range / paint / FT-driven)
- [ ] Solo carry ability (On/Off + teammate quality)
- [ ] Scoring consistency (game-to-game variance)
- [ ] Player evolution (early career vs prime vs late)
