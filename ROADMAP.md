# Roadmap: NBA Player Analysis System

## Core Philosophy

- Each dimension is an independent ranking with its own methodology
- Same rigor as Scoring: era-adjusted, data-driven, sensitivity-tested
- Composite ranking comes LAST, after all dimensions are solid
- **Data correctness before new features** — see "Fixed in the correctness pass" in README

## System Structure

```
NBA Player Analysis System
│
├── Offense
│   ├── Scoring (得分能力)              ✅ Done
│   ├── Offensive Impact (进攻影响力)    ✅ Done (ridge → O-DPM, CV Spearman 0.687)
│   └── Playmaking (组织能力)           ✅ Done (1977 前无 TOV, 已标记为估算)
│
├── Defense
│   ├── Overall Defensive Impact        ✅ Done (STL+BLK 代理 + D-DPM 模型)
│   ├── Rim Protection                  ⬜ Planned (需 BLK 位置数据)
│   └── Perimeter Defense               ⬜ Planned (需对位/防守难度数据)
│
├── Rebounding
│   ├── Offensive Rebounds              ✅ Done
│   └── Defensive Rebounds              ✅ Done
│
├── Basketball IQ
│   ├── Shot Selection (TS vs USG)      ⬜ Planned
│   ├── Turnover Rate                   🔶 Blocked — 1977-78 之前没有 TOV 数据
│   └── Clutch / Playoff Performance    🔶 Partial (季后赛 vs 常规赛已在仪表盘)
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
4. **Two-layer model** - All 101 players (basic data) + 56 modern (advanced data)
5. **Sensitivity analysis** - Test key parameters for stability
6. **Explanation layer** - Every ranking has factor-by-factor breakdown
7. **Out-of-sample validation** - Report CV metrics, never in-sample fit
8. **Explicit imputation** - 填充值必须打标记并出现在 UI 上, 不允许静默填充

## Data Needs

| Dimension | NBA API (have) | databallr (have) | Need to fetch |
|-----------|---------------|-----------------|---------------|
| Playmaking | APG, TOV (1977+) | PtsCreated, Assists/100, on-ball-time% | AST% from stat-nba |
| Defense | SPG, BPG (1973+) | D-DPM | DWS, 对位数据 |
| Rebounding | RPG, OREB/DREB (1973+) | - | - |
| Basketball IQ | FGA, TOV, TS% | playtype_diff, pt_adj_rTS | USG% |
| Legacy / Awards | - | - | MVP / All-NBA / 冠军 (`fetch_finals.py` 未接入) |
| 全联盟 Z-score | - | - | 联盟级赛季数据 (当前基准只是 101 人池) |

## Open Problems (from the correctness pass)

- [x] 多队赛季三重计算 → 已修, 有契约测试兜底
- [x] 名次截断造成的假并列 → 已修
- [x] 2025-26 赛季不完整 → 已用 B-R / ESPN 补齐
- [ ] 2002 年前的季后赛缺少独立数据源校验 (本机访问不到 stats.nba.com)
- [ ] 防守/篮板的缺失值用中位数/比例填充, 尚未做敏感性分析
- [ ] 中位数名次会制造并列 (scoring 85/101 个唯一名次), 可考虑改为 Z-score 均值

## Bonus Ideas
- [ ] Offensive style classification (3pt / mid-range / paint / FT-driven)
- [ ] Solo carry ability (On/Off + teammate quality)
- [ ] Scoring consistency (game-to-game variance)
- [ ] Player evolution (early career vs prime vs late)
