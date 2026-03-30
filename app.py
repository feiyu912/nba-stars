"""
NBA Player Analysis Dashboard
"""
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="NBA Player Analysis", layout="wide", page_icon="🏀")

# ── 加载数据 ──
@st.cache_data
def load_data():
    reg = pd.read_csv("data/nba100_career_all.csv")
    po = pd.read_csv("data/nba100_playoffs.csv")
    scoring = pd.read_csv("results/scoring_ranking.csv")
    impact = pd.read_csv("results/impact_ranking.csv")
    playmaking = pd.read_csv("results/playmaking_ranking.csv")

    career = reg.groupby("player").agg({
        "PPG": "mean", "FGM": "mean", "FG3M": "mean",
        "FTM": "mean", "TS_pct": "mean", "GP": "sum",
        "APG": "mean", "MIN": "mean",
        "TOV": "mean",
    }).round(3).reset_index()
    career["FG3M"] = career["FG3M"].fillna(0)
    career["FG2M"] = career["FGM"] - career["FG3M"]
    career["pts_2P"] = career["FG2M"] * 2
    career["pts_3P"] = career["FG3M"] * 3
    career["pts_FT"] = career["FTM"]
    career["pts_total"] = career["pts_2P"] + career["pts_3P"] + career["pts_FT"]
    career["pct_2P"] = (career["pts_2P"] / career["pts_total"] * 100).round(1)
    career["pct_3P"] = (career["pts_3P"] / career["pts_total"] * 100).round(1)
    career["pct_FT"] = (career["pts_FT"] / career["pts_total"] * 100).round(1)
    career["purity"] = (100 - career["pct_FT"]).round(1)
    career["TOV"] = career["TOV"].fillna(2.5)
    career["ast_tov"] = (career["APG"] / career["TOV"].replace(0, 0.5)).round(2)

    po_avg = po.groupby("player").agg({"PPG": "mean", "APG": "mean", "GP": "sum"}).round(2).reset_index()
    po_avg.columns = ["player", "po_PPG", "po_APG", "po_GP"]
    career = career.merge(po_avg, on="player", how="left")
    career["po_delta"] = (career["po_PPG"] - career["PPG"]).round(2)

    career = career.merge(scoring[["player", "scoring_rank"]], on="player", how="left")
    career = career.merge(impact[["player", "impact_rank"]], on="player", how="left")
    career = career.merge(playmaking[["player", "play_rank"]], on="player", how="left")

    return career

career = load_data()

# ── 标题 ──
st.title("🏀 NBA Player Analysis System")
st.markdown("**101 players | 1959-2026 | Multi-dimensional, era-adjusted rankings**")
st.markdown("---")

# ── 侧边栏: 分类导航 ──
st.sidebar.markdown("## 🏀 Offense")
off_views = [
    "Scoring Ranking",
    "Impact Ranking",
    "Playmaking Ranking",
    "Scoring Breakdown",
    "Playoff Performance",
    "Head-to-Head",
]
# st.sidebar.markdown("## 🛡️ Defense")  # 待开发
# st.sidebar.markdown("## 📊 Composite")  # 待开发
st.sidebar.markdown("## 🔎 Tools")
all_views = off_views + ["Player Lookup"]
view = st.sidebar.radio("Select view", all_views, label_visibility="collapsed")

st.sidebar.markdown("---")
top_n = st.sidebar.slider("Show top N players", 10, 101, 25)

# ════════════════════════════════
if view == "Scoring Ranking":
    st.header("📊 Scoring Ability")
    st.markdown("""
    **Who puts the ball in the basket best?**

    - **Scoring Index** = PPG (FT discounted 0.7x) x TS+ (relative efficiency)
    - **Playoff weight**: Each playoff game = 3x regular season
    - **Era adjustment**: Pace + competition intensity + scoring scarcity Z-score
    - **Two sub-views** (per-game + per-minute era-adjusted) combined via median rank

    *Assists and playmaking are NOT included — see Playmaking Ranking for that.*
    """)

    df = career.sort_values("scoring_rank").head(top_n).copy()
    df["Rank"] = df["scoring_rank"].astype(int)
    df = df.rename(columns={"player": "Player", "PPG": "PPG", "TS_pct": "TS%",
                              "pct_FT": "FT%ofScoring", "purity": "Purity%"})

    chart_df = df[["Rank", "Player", "PPG", "TS%"]].copy()
    chart_df["Label"] = chart_df.apply(lambda r: f"#{int(r['Rank'])} {r['Player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#00bcd4").encode(
        x=alt.X("PPG:Q", title="Career PPG"),
        y=alt.Y("Label:N", sort=alt.EncodingSortField(field="Rank", order="ascending"), title=""),
        tooltip=["Player", "Rank", "PPG", "TS%"]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    show_cols = ["Rank", "Player", "PPG", "TS%", "FT%ofScoring", "Purity%", "GP"]
    st.dataframe(df[show_cols].reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "Impact Ranking":
    st.header("⚡ Offensive Impact")
    st.markdown("""
    **Who contributes the most to team offense overall?**

    Includes scoring + assists + gravity + playmaking — the full picture.

    - Ridge regression trained on **O-DPM** (proxy target) with **era-adjusted Z-scores**
    - A player's stats are compared to their contemporaries, not raw values
    - 10 APG in the 1960s (rare) gets more credit than 10 APG today (more common)

    *Note: O-DPM is a proxy target, not ground truth.*
    """)

    df = career.sort_values("impact_rank").head(top_n).copy()
    df["Rank"] = df["impact_rank"].astype(int)

    chart_df = df[["impact_rank", "player", "PPG", "APG"]].copy()
    chart_df["Rank"] = chart_df["impact_rank"].astype(int)
    chart_df["Label"] = chart_df.apply(lambda r: f"#{int(r['Rank'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#ff9800").encode(
        x=alt.X("PPG:Q", title="Career PPG"),
        y=alt.Y("Label:N", sort=alt.EncodingSortField(field="Rank", order="ascending"), title=""),
        tooltip=["player", "Rank", "PPG", "APG"]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    show_cols = ["Rank", "player", "PPG", "APG", "TS_pct", "GP"]
    st.dataframe(df[show_cols].rename(columns={"player": "Player", "TS_pct": "TS%"}).reset_index(drop=True),
                 use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "Playmaking Ranking":
    st.header("🎯 Playmaking Ability")
    st.markdown("""
    **Who creates the most scoring opportunities for others?**

    Completely independent from Scoring — this measures what you create for teammates.

    - **Playmaking Index** = APG (pace-adjusted) x Assist-to-Turnover ratio x Scarcity
    - **Era-adjusted**: Averaging 10 APG in 1962 (only Oscar did it) counts more than 10 APG in 2025
    - **Playoff 3x weight**: Playmaking under pressure matters more
    - **AST/TOV**: Creating without wasting — John Stockton (3.7) vs Westbrook (2.0)

    *Scoring ability is NOT included — see Scoring Ranking for that.*
    """)

    df = career.sort_values("play_rank").head(top_n).copy()
    df["Rank"] = df["play_rank"].astype(int)

    chart_df = df[["play_rank", "player", "APG", "ast_tov"]].copy()
    chart_df["Rank"] = chart_df["play_rank"].astype(int)
    chart_df["Label"] = chart_df.apply(lambda r: f"#{int(r['Rank'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#4caf50").encode(
        x=alt.X("APG:Q", title="Career APG"),
        y=alt.Y("Label:N", sort=alt.EncodingSortField(field="Rank", order="ascending"), title=""),
        tooltip=["player", "Rank", "APG", "ast_tov"]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    show_cols = ["Rank", "player", "APG", "ast_tov", "GP"]
    st.dataframe(df[show_cols].rename(columns={
        "player": "Player", "ast_tov": "AST/TOV"
    }).reset_index(drop=True),
        use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "Scoring Breakdown":
    st.header("🔍 Scoring Structure")
    st.markdown("""
    **Where do the points come from?**

    - 🔵 **2-Point** (mid-range, drives, post-ups) | 🟠 **3-Point** (perimeter) | ⬜ **Free throws**
    - **Purity** = % from field goals. High purity = real shooting skill, not foul-drawing.
    - Players with high FT% are penalized in Scoring Ranking (FT x 0.7).
    """)

    df = career.sort_values("scoring_rank").head(top_n).copy()
    chart_df = df[["player", "pct_2P", "pct_3P", "pct_FT"]].set_index("player")
    chart_df.columns = ["2-Point %", "3-Point %", "Free Throw %"]
    st.bar_chart(chart_df, stack=True, color=["#2196F3", "#FF9800", "#9E9E9E"])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏆 Highest Purity (Shot-makers)")
        pure = career.sort_values("purity", ascending=False).head(10)
        st.dataframe(pure[["player", "PPG", "purity", "pct_2P", "pct_3P", "pct_FT"]].rename(
            columns={"player": "Player", "purity": "Purity%", "pct_2P": "2P%",
                     "pct_3P": "3P%", "pct_FT": "FT%"}).reset_index(drop=True),
            use_container_width=True)
    with col2:
        st.subheader("⚠️ Most FT-Dependent")
        impure = career.sort_values("purity").head(10)
        st.dataframe(impure[["player", "PPG", "purity", "pct_2P", "pct_3P", "pct_FT"]].rename(
            columns={"player": "Player", "purity": "Purity%", "pct_2P": "2P%",
                     "pct_3P": "3P%", "pct_FT": "FT%"}).reset_index(drop=True),
            use_container_width=True)

# ════════════════════════════════
elif view == "Playoff Performance":
    st.header("🔥 Playoff Performance")
    st.markdown("""
    **The biggest stage separates the great from the good.**

    Playoff PPG vs regular season PPG (minimum 30 playoff games).
    Playoff games are weighted 3x in all rankings.
    """)

    df = career[career["po_GP"] > 30].copy()
    df = df.sort_values("po_delta", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Biggest Risers")
        risers = df.head(15)[["player", "PPG", "po_PPG", "po_delta", "po_GP"]].copy()
        risers.columns = ["Player", "Reg PPG", "PO PPG", "Change", "PO Games"]
        st.dataframe(risers.reset_index(drop=True), use_container_width=True)
    with col2:
        st.subheader("📉 Biggest Drops")
        drops = df.tail(15).sort_values("po_delta")[["player", "PPG", "po_PPG", "po_delta", "po_GP"]].copy()
        drops.columns = ["Player", "Reg PPG", "PO PPG", "Change", "PO Games"]
        st.dataframe(drops.reset_index(drop=True), use_container_width=True)

    chart_df = df.head(20).set_index("player")[["po_delta"]].rename(columns={"po_delta": "PPG Change"})
    st.bar_chart(chart_df, color="#ffd700")

# ════════════════════════════════
elif view == "Head-to-Head":
    st.header("🔄 Cross-Ranking Comparison")
    st.markdown("""
    **Compare all three offensive dimensions side by side.**

    - **All-around offensive star**: High in all three
    - **Pure Scorer**: Scoring high, Playmaking low
    - **Pure Playmaker**: Playmaking high, Scoring low
    - **Score + Create**: Top 15 in both Scoring and Playmaking
    """)

    df = career.copy()
    df = df[df["scoring_rank"].notna() & df["play_rank"].notna()]

    compare = df[["player", "scoring_rank", "impact_rank", "play_rank", "PPG", "APG"]].copy()
    compare["scoring_rank"] = compare["scoring_rank"].astype(int)
    compare["impact_rank"] = compare["impact_rank"].astype(int)
    compare["play_rank"] = compare["play_rank"].astype(int)
    compare = compare.sort_values("scoring_rank").head(top_n)

    st.dataframe(compare.rename(columns={
        "player": "Player", "scoring_rank": "Scoring",
        "impact_rank": "Impact", "play_rank": "Playmaking"
    }).reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "Player Lookup":
    st.header("🔎 Player Lookup")
    st.markdown("**Complete offensive profile for any player.**")

    player = st.selectbox("Select player", sorted(career["player"].unique()))
    r = career[career["player"] == player].iloc[0]

    # 排名卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("📊 Scoring")
        scoring_rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else "N/A"
        st.metric("Rank", f"#{scoring_rk}")
        st.metric("PPG", f"{r['PPG']:.1f}")
        st.metric("TS%", f"{r['TS_pct']:.3f}")
        st.metric("Purity", f"{r['purity']:.1f}%")

    with col2:
        st.subheader("⚡ Impact")
        impact_rk = int(r["impact_rank"]) if pd.notna(r["impact_rank"]) else "N/A"
        st.metric("Rank", f"#{impact_rk}")
        st.metric("GP", f"{int(r['GP'])}")
        if pd.notna(r.get("po_PPG")):
            delta = r["po_PPG"] - r["PPG"]
            st.metric("Playoff PPG", f"{r['po_PPG']:.1f}", delta=f"{delta:+.1f}")
        else:
            st.metric("Playoff PPG", "N/A")

    with col3:
        st.subheader("🎯 Playmaking")
        play_rk = int(r["play_rank"]) if pd.notna(r["play_rank"]) else "N/A"
        st.metric("Rank", f"#{play_rk}")
        st.metric("APG", f"{r['APG']:.1f}")
        st.metric("AST/TOV", f"{r['ast_tov']:.1f}")

    # 得分结构
    st.subheader("Scoring Breakdown")
    breakdown = pd.DataFrame({
        "Source": ["2-Point", "3-Point", "Free Throw"],
        "Percentage": [r["pct_2P"], r["pct_3P"], r["pct_FT"]]
    }).set_index("Source")
    st.bar_chart(breakdown, color="#00bcd4")

    # 解释
    st.subheader("Analysis")
    factors = []
    if r["PPG"] > 25: factors.append(f"✅ High volume scorer (PPG={r['PPG']:.1f})")
    elif r["PPG"] > 20: factors.append(f"✅ Solid scorer (PPG={r['PPG']:.1f})")
    else: factors.append(f"⚠️ Lower scoring volume (PPG={r['PPG']:.1f})")

    if r["TS_pct"] > 0.58: factors.append(f"✅ Elite efficiency (TS%={r['TS_pct']:.3f})")
    elif r["TS_pct"] > 0.54: factors.append(f"✅ Good efficiency (TS%={r['TS_pct']:.3f})")
    else: factors.append(f"⚠️ Below-average efficiency (TS%={r['TS_pct']:.3f})")

    if r["pct_FT"] > 28: factors.append(f"⚠️ Heavy FT reliance ({r['pct_FT']:.1f}%)")
    elif r["pct_FT"] < 18: factors.append(f"✅ Low FT reliance ({r['pct_FT']:.1f}%)")

    if r["APG"] > 7: factors.append(f"✅ Elite playmaker (APG={r['APG']:.1f})")
    elif r["APG"] > 4: factors.append(f"✅ Good playmaker (APG={r['APG']:.1f})")
    else: factors.append(f"⚠️ Limited playmaking (APG={r['APG']:.1f})")

    if r["ast_tov"] > 2.5: factors.append(f"✅ Excellent decision-making (AST/TOV={r['ast_tov']:.1f})")
    elif r["ast_tov"] < 1.5: factors.append(f"⚠️ Turnover-prone (AST/TOV={r['ast_tov']:.1f})")

    if pd.notna(r.get("po_PPG")) and r["po_GP"] > 50:
        if r["po_PPG"] > r["PPG"]:
            factors.append(f"✅ Playoff riser ({r['po_PPG']:.1f} > {r['PPG']:.1f}, {int(r['po_GP'])} games)")
        else:
            factors.append(f"⚠️ Playoff decline ({r['po_PPG']:.1f} < {r['PPG']:.1f}, {int(r['po_GP'])} games)")
    elif pd.notna(r.get("po_GP")) and r["po_GP"] < 50:
        factors.append(f"⚠️ Limited playoff experience ({int(r['po_GP'])} games)")

    for f in factors:
        st.markdown(f)

# ── Footer ──
st.markdown("---")
st.markdown("""
*Data: NBA API (1959-2026) + databallr.com (2001-2026) | 101 players | All era-adjusted*
""")
