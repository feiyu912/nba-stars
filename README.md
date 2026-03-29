# NBA Historical Player Ranking System

101名NBA历史球员的多维度排名系统。用真实数据，让数据说话。

## Quick Start

```bash
# 安装依赖
pip install pandas scikit-learn nba_api requests streamlit matplotlib seaborn

# 启动交互式Dashboard
streamlit run app.py

# 运行排名模型
python notebooks/05_consensus_ranking.py

# 运行得分结构分析
python notebooks/06_scoring_breakdown.py
```

## Dashboard

运行 `streamlit run app.py` 后访问 http://localhost:8501

6个交互式视图:
- **Scoring Ranking** — 得分能力排名 (按排名排序的条形图 + 数据表)
- **Impact Ranking** — 进攻影响力排名
- **Head-to-Head** — 得分 vs 影响力象限图, 球员类型分类
- **Scoring Breakdown** — 得分结构拆解 (2P/3P/FT占比 + 纯度排名)
- **Playoff Performance** — 季后赛表现对比
- **Player Lookup** — 单个球员详情查询 + 排名原因解释

## 当前成果

### 两张独立排名表

**表1: 得分能力** — 谁最会进球？
- 得分指数 = PPG(罚球7折) x TS+(相对效率)
- 罚球惩罚: 罚球得分 x 0.7 (投篮进球含金量高于罚球)
- 季后赛加权: 每场季后赛 = 3倍常规赛 (季后赛已含总决赛)
- 时代修正: pace修正 + 竞争强度 sqrt(球队数/30) + 每分钟得分
- 两个子视角 A(每场高效得分) + C(时代修正) 取中位数

**表2: 进攻影响力** — 谁对球队进攻贡献最大？
- 用53名现代球员的O-DPM作为proxy target训练Ridge回归, 预测全部101人
- 注意: O-DPM本身是统计模型的产物, 不是ground truth
- 包含: 得分 + 助攻 + 引力 + 组织

### TOP 10

| 得分排名 | | 进攻影响力排名 | |
|----------|--|---------------|--|
| 1. Kevin Durant | | 1. Oscar Robertson | |
| 2. Michael Jordan | | 2. Nikola Jokic | |
| 3. Stephen Curry | | 3. Stephen Curry | |
| 4. Luka Doncic | | 4. Wilt Chamberlain | |
| 5. LeBron James | | 5. James Harden | |
| 6. Giannis | | 6. Luka Doncic | |
| 7. Joel Embiid | | 7. SGA | |
| 8. Nikola Jokic | | 8. Damian Lillard | |
| 9. Shaquille O'Neal | | 9. LeBron James | |
| 10. George Gervin | | 10. Michael Jordan | |

### 球员类型 (两表对比)

- **均衡型**: 乔丹、库里、詹姆斯、东契奇
- **纯得分手**: 科比、安东尼、奥尼尔、威尔金斯
- **组织型**: 纳什、斯托克顿、约基奇

### 关键发现

1. **季后赛表现区分真正的得分手** — 乔丹季后赛PPG 34.1 > 常规赛 29.5
2. **罚球占比影响排名** — 恩比德/哈登30%分靠罚球, 库里只有16%
3. **时代修正必不可少** — 张伯伦PPG 30.6但打45分钟+8支队
4. **得分能力和进攻影响力是两回事** — 纯得分手 vs 组织型差异大
5. **敏感性分析证明结果稳健** — FT系数0.6-0.8变化, TOP10最大波动2位

### 得分结构分析

- **三分型**: 库里(48%), 汤普森(51%), 东契奇(34%)
- **中近距离型**: 乔丹(72%), 奥尼尔(79%), 贾巴尔(83%)
- **罚球依赖型**: 恩比德(30%), 哈登(29%), 丹特利(30%)
- **得分纯度最高**: 汤普森(91.2%), 佩顿(85.0%), 库里(83.6%)

### 季后赛大赛型

- **越到大赛越强**: 约基奇(+5.4), 乔丹(+4.6), 诺维茨基(+4.5)
- **季后赛下降**: 张伯伦(-5.9), 丹特利(-3.6), 博什(-2.5)

## 方法论演化

1. 手动权重 -> 发现主观性太强
2. 用O-DPM做目标让模型学权重 -> 发现助攻权重被放大
3. 用PtsCreated做目标 -> 同样问题
4. 最终方案: **得分和影响力分开排名, 不混为一谈**
5. 逐步加入: 罚球惩罚、时代修正、季后赛加权、敏感性分析、解释层
6. 与O-DPM对标验证: 相关性r=0.555, 中等一致, 差异可解释

## 球员池

75大 (76人) + 当代巨星/近代名将 (25人) = 101人

## 数据源

| 数据源 | 覆盖 | 内容 |
|--------|------|------|
| **NBA API** | 1959-2026, 101人 | 常规赛1541赛季 + 季后赛1091赛季 |
| **databallr API** | 2001-2026, 53人x641赛季 | O-DPM, On-Off, rTS%, 388字段 |

## 项目结构

```
nba-stars/
├── app.py                          # Streamlit Dashboard
├── data/
│   ├── nba100_career_all.csv       # 101人常规赛数据
│   ├── nba100_playoffs.csv         # 101人季后赛数据
│   ├── nba100_databallr.csv        # 53人高阶数据
│   └── nba100_ids.json             # 球员ID映射
├── notebooks/
│   ├── 05_consensus_ranking.py     # 主模型: 得分+影响力排名
│   ├── 06_scoring_breakdown.py     # 得分结构拆解 + DPM对标
│   └── 07_visualization.py         # 静态图表生成
├── results/
│   ├── scoring_ranking.csv         # 得分能力排名
│   ├── impact_ranking.csv          # 进攻影响力排名
│   └── scoring_analysis.png        # 可视化图表
├── fetch_databallr_100.py          # databallr数据抓取
├── fetch_finals.py                 # 总决赛数据抓取 (备用)
├── README.md
└── archive/                        # 探索过程备份
```

## 质量验证

- **敏感性分析**: FT系数0.6-0.8, TOP10最大波动2位, 结果稳健
- **解释层**: TOP20球员均有排名原因分解
- **DPM对标**: 与专业指标相关性r=0.555, 差异可解释
- **已知局限**: O-DPM是proxy target; 现代球员数据更丰富; FT 0.7有主观成分

## 待开发

| 维度 | 状态 |
|------|------|
| 防守能力 | D-DPM数据就绪, 待建模 |
| 持久性/荣誉 | MVP/冠军/All-NBA, 待开始 |
| 最终综合排名 | 多维度总表, 待开始 |

## 技术栈

Python 3.12 | pandas | scikit-learn | nba_api | requests | Streamlit | Altair | Matplotlib
