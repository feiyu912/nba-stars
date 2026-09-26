"""界面文案的中英文对照。

规则: 选定语言后, 界面不允许出现另一种语言的文字。
例外只有两类, 都不属于"文案": 统计缩写 (只在中文里用中文术语, 如 PPG → 场均得分)
和球员姓名 (保留拉丁字母, 与数据表/结果文件一致)。

用法:
    from nbastars.i18n import t
    t("zh", "scoring_header")
    t("zh", "def_thin_body", n=8, names="A、B")
"""
from __future__ import annotations

LANGS = {"en": "English", "zh": "中文"}

STRINGS: dict[str, dict[str, str]] = {
    # ══ 全局 ══
    "en": {
        "app_title": "🏀 NBA Player Analysis System",
        "name_sep": ", ",
        "app_subtitle": "**101 players | 1948-2026 | multi-dimensional, era-adjusted rankings**",
        "app_data_note": (
            "Data scope: the league only started recording steals/blocks in 1973-74, turnovers in "
            "1977-78, and the offensive/defensive rebound split in 1973-74. **Missing values are "
            "always shown as N/A — nothing is estimated or filled in**, because a rank bought with "
            "filled-in values is a fake rank. Players missing a field are excluded from that "
            "dimension and listed on its page."
        ),
        "sidebar_category": "Category",
        "sidebar_view": "View",
        "sidebar_top_n": "Show top N players",
        "cat_offense": "🏀 Offense",
        "cat_defense": "🛡️ Defense",
        "cat_rebounding": "📊 Rebounding",
        "cat_lookup": "🔎 Player Lookup",
        "view_scoring": "Scoring Ranking",
        "view_impact": "Impact Ranking",
        "view_playmaking": "Playmaking Ranking",
        "view_breakdown": "Scoring Breakdown",
        "view_playoff": "Playoff Performance",
        "view_h2h": "Head-to-Head",
        "view_defense": "Defense Ranking",
        "view_rebounding": "Rebounding Ranking",
        "na": "N/A",
        "col_rank": "Rank",
        "col_player": "Player",
        "col_ppg": "Career PPG",
        "col_ts": "TS%",
        "col_apg": "Career APG",
        "col_gp": "Games",
        "col_playoff_gp": "Playoff games",
        "col_ft_share": "FT share of scoring",
        "col_purity": "Purity%",
        "col_stl": "Steals",
        "col_blk": "Blocks",
        "col_stl_blk": "STL+BLK",
        "col_sample": "Seasons with data",
        "col_rpg": "Career RPG",
        "col_orb": "Off. rebounds",
        "col_drb": "Def. rebounds",

        # ══ 得分 ══
        "scoring_header": "📊 Scoring Ability",
        "scoring_intro": (
            "**Who puts the ball in the basket best?**\n\n"
            "- **Scoring Index** = points per game (free throws discounted 0.7x) x TS+ (efficiency "
            "relative to the era)\n"
            "- **Playoff weight**: every playoff game counts 3x a regular-season game\n"
            "- **Era adjustment**: pace + competition depth + same-year scoring scarcity\n"
            "- **Two views** (per-game and per-minute, both era-adjusted) combined by median rank\n\n"
            "*Assists and playmaking are NOT included — see Playmaking Ranking for that.*"
        ),

        # ══ 影响力 ══
        "impact_header": "⚡ Offensive Impact",
        "impact_intro": (
            "**Who contributes the most to the team offense overall?**\n\n"
            "Scoring + assists + gravity + playmaking — the full picture.\n\n"
            "- Ridge regression trained on **O-DPM** (a proxy target) using **era-adjusted Z-scores**\n"
            "- A player's stats are compared with his contemporaries, not with raw values\n"
            "- 10 assists per game in the 1960s (rare) counts for more than 10 today (common)\n\n"
            "*O-DPM is a proxy target, not ground truth.*"
        ),

        # ══ 组织 ══
        "play_header": "🎯 Playmaking Ability",
        "play_intro": (
            "**Who creates the most scoring opportunities for others?**\n\n"
            "Fully independent from Scoring — this measures what you create for teammates.\n\n"
            "- **Playmaking Index** = assists per game (pace-adjusted) x assist-to-turnover ratio x "
            "scarcity\n"
            "- **Era-adjusted**: averaging 10 assists in 1962 (only Oscar did it) counts for more "
            "than 10 in 2025\n"
            "- **Playoff 3x weight**: creating under pressure matters more\n"
            "- **AST/TOV**: creating without wasting possessions — Stockton (3.7) vs Westbrook (2.0)\n\n"
            "*Turnovers were not recorded before 1977-78, so AST/TOV for those players is estimated "
            "from a league-average turnover count and marked **Estimated** — never silently filled.*"
        ),

        # ══ 得分结构 ══
        "bd_header": "🔍 Scoring Structure",
        "bd_intro": (
            "**Where do the points come from?**\n\n"
            "- 🔵 **2-point** (mid-range, drives, post-ups) | 🟠 **3-point** (perimeter) | ⬜ **Free "
            "throws**\n"
            "- **Purity** = share of points from field goals. High purity means real shooting skill, "
            "not foul-drawing.\n"
            "- Players who lean on free throws are discounted in the Scoring Ranking (FT x 0.7)."
        ),
        "bd_2p": "2-Point %",
        "bd_3p": "3-Point %",
        "bd_ft": "Free Throw %",
        "bd_top_purity": "🏆 Highest Purity (shot-makers)",
        "bd_top_ft": "⚠️ Most FT-dependent",

        # ══ 季后赛 ══
        "po_header": "🔥 Playoff Performance",
        "po_intro": (
            "**The biggest stage separates the great from the good.**\n\n"
            "Playoff scoring vs regular-season scoring (minimum 30 playoff games). "
            "Playoff games are weighted 3x in every ranking."
        ),
        "po_risers": "📈 Biggest risers",
        "po_drops": "📉 Biggest drops",
        "po_col_reg": "Regular season",
        "po_col_po": "Playoffs",
        "po_col_change": "Change",
        "po_col_games": "Playoff games",

        # ══ 对比 ══
        "h2h_header": "🔄 Cross-Ranking Comparison",
        "h2h_intro": (
            "**Compare the dimensions side by side.**\n\n"
            "- **All-around offensive star**: high in all three offensive dimensions\n"
            "- **Pure scorer**: scoring high, playmaking low\n"
            "- **Pure playmaker**: playmaking high, scoring low\n"
            "- **Score + create**: top 15 in both scoring and playmaking"
        ),

        # ══ 防守 ══
        "def_header": "🛡️ Defensive Ability",
        "def_intro": (
            "**Who is the best defender in NBA history?**\n\n"
            "- **Defense output** = steals + blocks, pace-adjusted\n"
            "- **Era scarcity**: dominating defensively in a low-steal/block era earns extra credit\n"
            "- **Playoff experience bonus**: more playoff games = defense trusted under pressure\n"
            "- Two views (per-game and per-minute, both era-adjusted) combined by median rank\n\n"
            "⚠️ **The NBA did not record steals or blocks before 1973-74.** Anything before that has "
            "no defensive data, and **nothing is estimated** — an estimate would produce a fake rank. "
            "Affected players show **N/A** and are not ranked."
        ),
        "def_chart_x": "Career steals + blocks",
        "def_excluded_title": "**Not ranked: {n} players**",
        "def_excluded_body": (
            "no steals/blocks exist for them (careers entirely before 1973-74): {names}"
        ),
        "def_thin_title": "**Not ranked: {n} players with too few seasons**",
        "def_thin_body": (
            "the peak window is {peak} seasons; with fewer than that the \"peak\" is just an average "
            "of 1-4 seasons and the rank is not comparable. Also excluded are players with no "
            "defensive data at all. Excluded: {names}"
        ),

        # ══ 篮板 ══
        "reb_header": "🏀 Rebounding Ability",
        "reb_intro": (
            "**Who controls the boards?**\n\n"
            "- **Total rebounds per game** (pace-adjusted) with an era scarcity bonus\n"
            "- **ORB** = offensive rebounds (creating second chances)\n"
            "- **DRB** = defensive rebounds (ending opponent possessions)\n"
            "- Playoff experience bonus applied\n\n"
            "⚠️ **The NBA only split rebounds into offensive/defensive in 1973-74.** Total rebounds "
            "(recorded since 1950-51) are ranked as usual; players without the split show **N/A** "
            "for ORB/DRB and the split is never estimated."
        ),
        "reb_chart_x": "Career rebounds per game",
        "reb_excluded_title": "**No offensive/defensive split: {n} players**",
        "reb_excluded_body": (
            "careers entirely before 1973-74: {names} — their total-rebound rank is valid, ORB/DRB "
            "are N/A."
        ),

        # ══ 球员查询 ══
        "lk_header": "🔎 Player Lookup",
        "lk_intro": "**Complete player profile across all dimensions.**",
        "lk_select": "Select player",
        "lk_scoring": "📊 Scoring",
        "lk_impact": "⚡ Impact",
        "lk_playmaking": "🎯 Playmaking",
        "lk_def_reb": "🛡️ Defense / 🏀 Rebounds",
        "lk_rank": "Rank",
        "lk_def_rank": "Defense rank",
        "lk_reb_rank": "Rebound rank",
        "lk_ppg": "Points per game",
        "lk_ts": "TS%",
        "lk_purity": "Purity",
        "lk_gp": "Games",
        "lk_po_ppg": "Playoff PPG",
        "lk_apg": "Assists per game",
        "lk_ast_tov": "AST/TOV",
        "lk_rpg": "Rebounds per game",
        "lk_orb_drb": "ORB / DRB",
        "lk_breakdown": "Scoring breakdown",
        "lk_analysis": "Analysis",
        "lk_src_2p": "2-point",
        "lk_src_3p": "3-point",
        "lk_src_ft": "Free throw",

        # ══ 解释层 ══
        "f_high_volume": "✅ High-volume scorer ({ppg:.1f} points per game for his career)",
        "f_solid_scorer": "✅ Solid scorer ({ppg:.1f} points per game for his career)",
        "f_low_volume": "⚠️ Below-average scoring volume ({ppg:.1f} points per game)",
        "f_elite_eff": "✅ Elite efficiency (TS% = {ts:.3f})",
        "f_good_eff": "✅ Good efficiency (TS% = {ts:.3f})",
        "f_low_eff": "⚠️ Below-average efficiency (TS% = {ts:.3f})",
        "f_heavy_ft": "⚠️ Leans heavily on free throws ({ft:.1f}% of his points)",
        "f_low_ft": "✅ Rarely relies on free throws ({ft:.1f}% of his points)",
        "f_elite_playmaker": "✅ Elite playmaker ({apg:.1f} assists per game)",
        "f_good_playmaker": "✅ Good playmaker ({apg:.1f} assists per game)",
        "f_limited_playmaking": "⚠️ Limited playmaking ({apg:.1f} assists per game)",
        "f_no_tov": "➖ No turnover record (the stat only exists from 1977-78), so AST/TOV is not judged",
        "f_excellent_decision": "✅ Excellent decision-making (AST/TOV = {ratio:.2f})",
        "f_turnover_prone": "⚠️ Turnover-prone (AST/TOV = {ratio:.2f})",
        "f_po_riser": "✅ Raises his game in the playoffs ({po:.1f} vs {reg:.1f}, {games} games)",
        "f_po_decline": "⚠️ Declines in the playoffs ({po:.1f} vs {reg:.1f}, {games} games)",
        "f_limited_po": "⚠️ Limited playoff experience ({games} games)",

        # ══ 新分类 / 新视图 ══
        "page_title": "NBA Player Analysis",
        "cat_compare": "🔀 Cross-dimension",
        "view_def_split": "Steals & Blocks",
        "view_def_impact": "Defensive Impact",
        "view_reb_split": "Off / Def Rebounds",
        "col_peak": "Peak 5-season avg",
        "col_estimated": "Estimated",
        "play_tov_note": (
            "Turnovers were not recorded before 1977-78. For players whose careers began before "
            "then, AST/TOV is not missing data — it is *estimated* from a league-average turnover "
            "count, and the whole playmaking index is multiplied by that estimate. Affected "
            "players are marked **Estimated**: {names}"
        ),
        "thin_name_item": "{name} ({n} seasons)",
        "bd_share": "Share of points (%)",
        "lk_source": "Source",

        "def_split_header": "🛡️ Steals vs Blocks",
        "def_split_intro": (
            "**Two different defensive skills.** Steals measure perimeter anticipation, blocks "
            "measure rim protection — combining them into one number lets a guard's steals and a "
            "centre's blocks cancel each other out.\n\n"
            "Both rankings use the same era-adjusted, two-view engine as the main defense ranking, "
            "and the same sample rule: players without steals/blocks data, or with fewer than 5 "
            "seasons of it, are not ranked."
        ),
        "def_split_stl": "🏃 Top steals",
        "def_split_blk": "🚫 Top blocks",

        "def_impact_header": "📉 Defensive Impact",
        "def_impact_intro": (
            "**Ridge regression trained on D-DPM** (a third-party defensive metric, used as a proxy "
            "target). Features are era-adjusted steals/blocks Z-scores plus career rebounds.\n\n"
            "*D-DPM is a proxy, not ground truth — the model measures how well box scores reproduce "
            "that metric, not true defensive impact.*"
        ),
        "imp_predicted": "Model prediction",
        "imp_actual": "Actual D-DPM",
        "def_impact_model": (
            "Model quality: {n} training players, 5-fold cross-validated R² = {r2:.3f}, "
            "Spearman = {rho:.3f}"
        ),

        "reb_split_header": "🏀 Offensive vs Defensive Rebounds",
        "reb_split_intro": (
            "**Creating second chances vs ending possessions.** Offensive rebounds extend a "
            "possession; defensive rebounds end the opponent's. The two reward different skills, so "
            "they are ranked separately here.\n\n"
            "Both use the peak-5-season average of the per-game rate. The 11 players whose careers "
            "ended before 1973-74 have no split at all and are not ranked; their total-rebound rank "
            "on the main page is unaffected."
        ),
        "reb_split_orb": "🔥 Top offensive rebounders",
        "reb_split_drb": "🧱 Top defensive rebounders",

        "po_metric": "Metric",
        "po_metric_scoring": "Scoring",
        "po_metric_rebounds": "Rebounds",
        "po_metric_assists": "Assists",
        "po_chart": "{metric} change in the playoffs",

        # ══ 页脚 ══
        "footer_sources": (
            "*Regular season: NBA.com official API (1948-2024) + Basketball-Reference (2025-26) | "
            "Playoffs: NBA.com + ESPN (2025-26)*"
        ),
        "footer_notes": (
            "*101 players | era adjustments: pace / competition depth / scarcity | multi-team "
            "seasons count only the combined row | data verification: scripts/verify_*.py*"
        ),
    },

    "zh": {
        "app_title": "🏀 NBA 球员分析系统",
        "name_sep": "、",
        "app_subtitle": "**101 名球员 | 1948-2026 | 多维度、时代修正排名**",
        "app_data_note": (
            "数据口径：联盟从 1973-74 赛季才开始记录抢断/盖帽、从 1977-78 赛季才开始记录失误、"
            "1973-74 赛季才区分进攻/防守篮板。**缺失处一律显示「无数据」，不做任何估算填充** —— "
            "用填充值换来的名次是假名次。缺这些字段的球员会从对应维度里排除，并在该页列出名单。"
        ),
        "sidebar_category": "分类",
        "sidebar_view": "视图",
        "sidebar_top_n": "显示前 N 名",
        "cat_offense": "🏀 进攻",
        "cat_defense": "🛡️ 防守",
        "cat_rebounding": "📊 篮板",
        "cat_lookup": "🔎 球员查询",
        "view_scoring": "得分排名",
        "view_impact": "进攻影响力排名",
        "view_playmaking": "组织能力排名",
        "view_breakdown": "得分结构",
        "view_playoff": "季后赛表现",
        "view_h2h": "跨维度对比",
        "view_defense": "防守排名",
        "view_rebounding": "篮板排名",
        "na": "无数据",
        "col_rank": "名次",
        "col_player": "球员",
        "col_ppg": "生涯场均得分",
        "col_ts": "真实命中率",
        "col_apg": "生涯场均助攻",
        "col_gp": "出场数",
        "col_playoff_gp": "季后赛出场",
        "col_ft_share": "罚球占得分比",
        "col_purity": "投篮纯度",
        "col_stl": "场均抢断",
        "col_blk": "场均盖帽",
        "col_stl_blk": "抢断+盖帽",
        "col_sample": "有效赛季数",
        "col_rpg": "生涯场均篮板",
        "col_orb": "场均进攻篮板",
        "col_drb": "场均防守篮板",

        "scoring_header": "📊 得分能力",
        "scoring_intro": (
            "**谁最擅长把球放进篮筐？**\n\n"
            "- **得分指数** = 场均得分（罚球按 0.7 折算）× 相对效率（真实命中率 ÷ 同时代联盟平均）\n"
            "- **季后赛加权**：每场季后赛按 3 场常规赛计算\n"
            "- **时代修正**：节奏 + 联盟深度 + 同年得分稀缺度\n"
            "- **两个视角**（场均与每分钟，均已做时代修正）取中位数名次合并\n\n"
            "*这里不含助攻和组织 —— 见「组织能力排名」。*"
        ),

        "impact_header": "⚡ 进攻影响力",
        "impact_intro": (
            "**谁对球队进攻的整体贡献最大？**\n\n"
            "包含得分、助攻、牵制力和组织 —— 完整画面。\n\n"
            "- 岭回归模型，目标是 **O-DPM**（代理指标），特征是**时代修正后的 Z 分数**\n"
            "- 球员的数据与同时代球员比较，而不是看原始数值\n"
            "- 1960 年代场均 10 次助攻（当时极罕见）比今天的 10 次（常见）更值钱\n\n"
            "*O-DPM 是代理指标，不是真值。*"
        ),

        "play_header": "🎯 组织能力",
        "play_intro": (
            "**谁为队友创造的机会最多？**\n\n"
            "与得分完全独立 —— 这里衡量的是你为队友创造了什么。\n\n"
            "- **组织指数** = 场均助攻（节奏修正）× 助攻失误比 × 稀缺度\n"
            "- **时代修正**：1962 年场均 10 次助攻（只有 Oscar Robertson 做到）比 2025 年的 10 次更难得\n"
            "- **季后赛 3 倍加权**：压力下的组织更值钱\n"
            "- **助攻失误比**：创造而不浪费 —— Stockton（3.7）对 Westbrook（2.0）\n\n"
            "*1977-78 赛季之前不记录失误，这些球员的助攻失误比是按联盟平均误差数估算的，表中标为**估算** —— "
            "不做静默填充。*"
        ),

        "bd_header": "🔍 得分结构",
        "bd_intro": (
            "**得分都来自哪里？**\n\n"
            "- 🔵 **两分**（中距离、突破、低位） | 🟠 **三分**（外线） | ⬜ **罚球**\n"
            "- **投篮纯度** = 来自运动战的得分占比。纯度高说明是真投篮能力，而不是靠造犯规。\n"
            "- 依赖罚球的球员在得分排名里会被折算（罚球 × 0.7）。"
        ),
        "bd_2p": "两分占比",
        "bd_3p": "三分占比",
        "bd_ft": "罚球占比",
        "bd_top_purity": "🏆 投篮纯度最高",
        "bd_top_ft": "⚠️ 最依赖罚球",

        "po_header": "🔥 季后赛表现",
        "po_intro": (
            "**最大的舞台区分伟大与优秀。**\n\n"
            "季后赛场均得分与常规赛场均得分的对比（至少打过 30 场季后赛）。"
            "所有排名中季后赛都按 3 倍加权。"
        ),
        "po_risers": "📈 提升最大",
        "po_drops": "📉 下滑最大",
        "po_col_reg": "常规赛",
        "po_col_po": "季后赛",
        "po_col_change": "变化",
        "po_col_games": "季后赛场次",

        "h2h_header": "🔄 跨维度对比",
        "h2h_intro": (
            "**把各个维度放在一起看。**\n\n"
            "- **全能进攻核心**：三个进攻维度都靠前\n"
            "- **纯得分手**：得分高、组织低\n"
            "- **纯组织者**：组织高、得分低\n"
            "- **得分兼组织**：得分与组织都进前 15"
        ),

        "def_header": "🛡️ 防守能力",
        "def_intro": (
            "**谁是 NBA 历史上最好的防守者？**\n\n"
            "- **防守产出** = 抢断 + 盖帽，已做节奏修正\n"
            "- **时代稀缺性**：在抢断/盖帽普遍偏低的年代打出统治力，额外加分\n"
            "- **季后赛经验加成**：季后赛打得越多，说明防守越被信任\n"
            "- 两个视角（场均与每分钟，均已做时代修正）取中位数名次合并\n\n"
            "⚠️ **NBA 直到 1973-74 赛季才开始记录抢断和盖帽。** 在此之前没有任何防守数据，"
            "这里**不做任何估算** —— 估算出来的名次是假名次。相关球员显示**无数据**，不参与排名。"
        ),
        "def_chart_x": "生涯场均抢断+盖帽",
        "def_excluded_title": "**不参与排名：{n} 人**",
        "def_excluded_body": "他们的生涯全部在 1973-74 之前，没有任何抢断/盖帽记录：{names}",
        "def_thin_title": "**不参与排名：{n} 人有效赛季不足**",
        "def_thin_body": (
            "巅峰窗口按 {peak} 个赛季计算，不足 {peak} 个赛季时「巅峰值」只是 1-4 个赛季的平均，"
            "名次没有可比性，因此同样排除。被排除的球员：{names}"
        ),

        "reb_header": "🏀 篮板能力",
        "reb_intro": (
            "**谁掌控篮板？**\n\n"
            "- **场均总篮板**（节奏修正）并叠加时代稀缺度加成\n"
            "- **进攻篮板**：创造二次进攻机会\n"
            "- **防守篮板**：终结对手回合\n"
            "- 应用季后赛经验加成\n\n"
            "⚠️ **NBA 直到 1973-74 赛季才区分进攻/防守篮板。** 总篮板（1950-51 赛季起有记录）"
            "照常排名；没有拆分的球员进攻/防守篮板显示**无数据**，不做任何比例估算。"
        ),
        "reb_chart_x": "生涯场均篮板",
        "reb_excluded_title": "**没有进攻/防守篮板拆分：{n} 人**",
        "reb_excluded_body": "他们的生涯全部在 1973-74 之前：{names} —— 总篮板名次有效，进攻/防守篮板为无数据。",

        "lk_header": "🔎 球员查询",
        "lk_intro": "**一名球员在所有维度上的完整画像。**",
        "lk_select": "选择球员",
        "lk_scoring": "📊 得分",
        "lk_impact": "⚡ 影响力",
        "lk_playmaking": "🎯 组织",
        "lk_def_reb": "🛡️ 防守 / 🏀 篮板",
        "lk_rank": "名次",
        "lk_def_rank": "防守名次",
        "lk_reb_rank": "篮板名次",
        "lk_ppg": "场均得分",
        "lk_ts": "真实命中率",
        "lk_purity": "投篮纯度",
        "lk_gp": "出场数",
        "lk_po_ppg": "季后赛场均得分",
        "lk_apg": "场均助攻",
        "lk_ast_tov": "助攻失误比",
        "lk_rpg": "场均篮板",
        "lk_orb_drb": "进攻 / 防守篮板",
        "lk_breakdown": "得分结构",
        "lk_analysis": "分析",
        "lk_src_2p": "两分",
        "lk_src_3p": "三分",
        "lk_src_ft": "罚球",

        "f_high_volume": "✅ 高产得分手（生涯场均 {ppg:.1f} 分）",
        "f_solid_scorer": "✅ 稳定得分手（生涯场均 {ppg:.1f} 分）",
        "f_low_volume": "⚠️ 得分产量偏低（生涯场均 {ppg:.1f} 分）",
        "f_elite_eff": "✅ 效率顶级（真实命中率 {ts:.3f}）",
        "f_good_eff": "✅ 效率良好（真实命中率 {ts:.3f}）",
        "f_low_eff": "⚠️ 效率偏低（真实命中率 {ts:.3f}）",
        "f_heavy_ft": "⚠️ 高度依赖罚球（{ft:.1f}% 的得分来自罚球）",
        "f_low_ft": "✅ 几乎不依赖罚球（{ft:.1f}% 的得分来自罚球）",
        "f_elite_playmaker": "✅ 顶级组织者（场均 {apg:.1f} 次助攻）",
        "f_good_playmaker": "✅ 优秀组织者（场均 {apg:.1f} 次助攻）",
        "f_limited_playmaking": "⚠️ 组织能力有限（场均 {apg:.1f} 次助攻）",
        "f_no_tov": "➖ 没有失误记录（该统计从 1977-78 赛季起才有），助攻失误比不参与判断",
        "f_excellent_decision": "✅ 决策出色（助攻失误比 {ratio:.2f}）",
        "f_turnover_prone": "⚠️ 容易失误（助攻失误比 {ratio:.2f}）",
        "f_po_riser": "✅ 季后赛更强（{po:.1f} 对 {reg:.1f}，{games} 场）",
        "f_po_decline": "⚠️ 季后赛下滑（{po:.1f} 对 {reg:.1f}，{games} 场）",
        "f_limited_po": "⚠️ 季后赛经验有限（{games} 场）",

        "page_title": "NBA 球员分析",
        "cat_compare": "🔀 横向对比",
        "view_def_split": "抢断与盖帽",
        "view_def_impact": "防守影响力",
        "view_reb_split": "进攻与防守篮板",
        "col_peak": "巅峰 5 年均值",
        "col_estimated": "估算",
        "play_tov_note": (
            "1977-78 赛季之前不记录失误。对这些球员来说，助失比不是「缺数据」，而是**用联盟平均"
            "失误数估算出来的**，而且整个组织指数都要乘以这个估算值 —— 他们的名次因此含估算成分，"
            "已在表中标为**估算**：{names}"
        ),
        "thin_name_item": "{name}（{n} 个赛季）",
        "bd_share": "得分占比（%）",
        "lk_source": "得分来源",

        "def_split_header": "🛡️ 抢断与盖帽",
        "def_split_intro": (
            "**两种不同的防守技能。** 抢断体现外线预判，盖帽体现护框 —— 合成一个「防守产出」会让"
            "后卫的抢断和中锋的盖帽互相抵消。\n\n"
            "两个榜单沿用主防守榜同一套时代修正与双视角算法，最小样本规则也相同：没有抢断/盖帽数据、"
            "或有效赛季不足 5 个的球员不参与排名。"
        ),
        "def_split_stl": "🏃 抢断榜",
        "def_split_blk": "🚫 盖帽榜",

        "def_impact_header": "📉 防守影响力",
        "def_impact_intro": (
            "**用岭回归拟合 D-DPM**（第三方防守指标，作为代理目标）。特征是时代修正后的抢断/盖帽 "
            "Z 分数，加上生涯篮板。\n\n"
            "*D-DPM 是代理指标，不是真值 —— 模型衡量的是「基础数据能在多大程度上复现该指标」，"
            "不代表真实的防守影响力。*"
        ),
        "imp_predicted": "模型预测值",
        "imp_actual": "实际 D-DPM",
        "def_impact_model": "模型质量：训练样本 {n} 人，5 折交叉验证 R² = {r2:.3f}，Spearman = {rho:.3f}",

        "reb_split_header": "🏀 进攻篮板与防守篮板",
        "reb_split_intro": (
            "**创造二次机会，还是终结对手回合？** 进攻篮板延续进攻机会，防守篮板上终结对手的回合，"
            "两种能力奖励的东西不同，所以分开排名。\n\n"
            "两个榜都用场均数据的巅峰 5 年均值。生涯全部在 1973-74 之前的 11 名球员没有拆分数据，"
            "不参与排名；他们在主榜上的总篮板名次不受影响。"
        ),
        "reb_split_orb": "🔥 进攻篮板榜",
        "reb_split_drb": "🧱 防守篮板榜",

        "po_metric": "指标",
        "po_metric_scoring": "得分",
        "po_metric_rebounds": "篮板",
        "po_metric_assists": "助攻",
        "po_chart": "季后赛{metric}的变化",

        "footer_sources": (
            "*常规赛：NBA.com 官方接口（1948-2024）+ Basketball-Reference（2025-26）| "
            "季后赛：NBA.com + ESPN（2025-26）*"
        ),
        "footer_notes": (
            "*101 名球员 | 时代修正：节奏 / 联盟深度 / 稀缺度 | 多队赛季只计合并数据 | "
            "数据校验脚本：scripts/verify_*.py*"
        ),
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """取文案。缺键时直接抛错 —— 宁可报错也不要静默显示成另一种语言。"""
    try:
        text = STRINGS[lang][key]
    except KeyError as exc:
        raise KeyError(f"缺少文案: lang={lang!r} key={key!r}") from exc
    return text.format(**kwargs) if kwargs else text


def check_complete() -> list[str]:
    """两种语言的键必须一一对应, 供测试使用"""
    en, zh = set(STRINGS["en"]), set(STRINGS["zh"])
    return sorted(f"en-only: {k}" for k in en - zh) + sorted(f"zh-only: {k}" for k in zh - en)
