"""
NBA Scoring Analysis Dashboard
"""
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="NBA Scoring Analysis", layout="wide", page_icon="🏀")

# ── 加载数据 ──
@st.cache_data
def load_data():
    reg = pd.read_csv("data/nba100_career_all.csv")
    po = pd.read_csv("data/nba100_playoffs.csv")
    scoring = pd.read_csv("results/scoring_ranking.csv")
    impact = pd.read_csv("results/impact_ranking.csv")

    career = reg.groupby("player").agg({
        "PPG": "mean", "FGM": "mean", "FG3M": "mean",
        "FTM": "mean", "TS_pct": "mean", "GP": "sum",
        "APG": "mean", "MIN": "mean",
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

    po_avg = po.groupby("player").agg({"PPG": "mean", "GP": "sum"}).round(2).reset_index()
    po_avg.columns = ["player", "po_PPG", "po_GP"]
    career = career.merge(po_avg, on="player", how="left")
    career["po_delta"] = (career["po_PPG"] - career["PPG"]).round(2)

    career = career.merge(scoring[["player", "scoring_rank"]], on="player", how="left")
    career = career.merge(impact[["player", "impact_rank"]], on="player", how="left")

    return career, scoring, impact

career, scoring, impact = load_data()

# ── 标题 ──
st.title("🏀 NBA Historical Scoring Analysis")
st.markdown("**101 players | 1959-2026 | Data-driven ranking system**")
st.markdown("---")

# ── 侧边栏 ──
st.sidebar.header("Controls")
top_n = st.sidebar.slider("Show top N players", 10, 101, 25)
view = st.sidebar.radio("View", ["Scoring Ranking", "Impact Ranking", "Head-to-Head",
                                   "Scoring Breakdown", "Playoff Performance", "Player Lookup"])

# ════════════════════════════════
if view == "Scoring Ranking":
    st.header("📊 Scoring Ability Ranking")
    st.markdown("""
    **Who is the best scorer in NBA history?**

    This ranking measures pure scoring ability: how many points you put in the basket, and how efficiently.

    **Method:**
    - **Scoring Index** = PPG (FT discounted 0.7x) x TS+ (relative efficiency)
    - **Playoff weight**: Each playoff game counts 3x a regular season game (playoffs include Finals)
    - **Era adjustment**: Pace correction + competition intensity sqrt(teams/30)
    - **Scoring scarcity**: Players who dominate in low-scoring eras get extra credit (Z-score bonus)
    - **Two sub-views** (A: per-game scoring, C: per-minute era-adjusted) combined via median rank

    *Assists, playmaking, and gravity effects are NOT included — those belong in the Impact Ranking.*
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
    st.header("⚡ Offensive Impact Ranking")
    st.markdown("""
    **Who contributes the most to team offense?**

    This ranking measures total offensive impact: scoring + assists + gravity + playmaking.
    It's fundamentally different from the Scoring Ranking.

    **Method:**
    - Ridge regression trained on **O-DPM** (Offensive Daily Plus-Minus) as proxy target
    - Features are **era-adjusted Z-scores**: a player's stats are compared to their contemporaries
    - This means a player averaging 10 APG in the 1960s (when nobody else did) gets more credit
      than 10 APG today (when it's more common)
    - Trained on 53 modern players with O-DPM data, then applied to all 101 players

    *Note: O-DPM is itself a statistical model output, not ground truth. Results are approximate.*
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
elif view == "Head-to-Head":
    st.header("🔄 Scoring vs Impact: Player Types")
    st.markdown("""
    **What kind of offensive player are you?**

    By comparing Scoring Rank vs Impact Rank, we can classify players into three types:
    - **🎯 Pure Scorer** (Scoring >> Impact): Scores a lot but doesn't create for others. *e.g. Kobe, Carmelo, Shaq*
    - **🎨 Playmaker** (Impact >> Scoring): Elevates the whole offense beyond just scoring. *e.g. Nash, Stockton, Jokic*
    - **⚖️ Balanced** (Both similar): Elite at scoring AND creating. *e.g. Jordan, Curry, LeBron*

    Both rankings are era-adjusted. Gap = Impact Rank - Scoring Rank (positive = pure scorer).
    """)

    both = career[(career["scoring_rank"].notna()) & (career["impact_rank"].notna())].copy()
    both = both[both["scoring_rank"] <= top_n]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Scatter: Score Rank vs Impact Rank")
        scatter_data = both[["player", "scoring_rank", "impact_rank"]].copy()
        scatter_data["diff"] = scatter_data["impact_rank"] - scatter_data["scoring_rank"]
        scatter_data["type"] = scatter_data["diff"].apply(
            lambda d: "Pure Scorer" if d > 10 else ("Playmaker" if d < -10 else "Balanced"))
        st.scatter_chart(scatter_data, x="scoring_rank", y="impact_rank", color="type", size=60)

    with col2:
        st.subheader("Player Type Classification")
        compare = both[["player", "scoring_rank", "impact_rank"]].copy()
        compare["diff"] = compare["impact_rank"] - compare["scoring_rank"]
        compare["Type"] = compare["diff"].apply(
            lambda d: "🎯 Pure Scorer" if d > 10 else ("🎨 Playmaker" if d < -10 else "⚖️ Balanced"))
        compare = compare.sort_values("scoring_rank")
        st.dataframe(compare.rename(columns={"player": "Player", "scoring_rank": "Score Rk",
                                               "impact_rank": "Impact Rk", "diff": "Gap"}).reset_index(drop=True),
                     use_container_width=True, height=min(top_n * 38, 600))

# ════════════════════════════════
elif view == "Scoring Breakdown":
    st.header("🔍 Scoring Structure Breakdown")
    st.markdown("""
    **Where do the points come from?**

    Every point is scored in one of three ways:
    - 🔵 **2-Point field goals** (mid-range, drives, post-ups)
    - 🟠 **3-Point field goals** (perimeter shooting)
    - ⬜ **Free throws** (foul shots)

    **Scoring Purity** = % of points from actual field goals (2P + 3P).
    High purity = scores from real shooting skill. Low purity = relies on getting to the foul line.

    *Players with high FT% are penalized in the Scoring Ranking (FT x 0.7 discount).*
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
    st.header("🔥 Playoff Performance: Who Steps Up?")
    st.markdown("""
    **The biggest stage separates the great from the good.**

    This compares each player's playoff PPG vs regular season PPG (minimum 30 playoff games).

    - **📈 Risers**: Score MORE in the playoffs — the true big-game players
    - **📉 Droppers**: Score LESS in the playoffs — may struggle under pressure or tighter defense

    *Playoff games are weighted 3x in the Scoring Ranking, so playoff risers get a significant boost.*
    """)

    df = career[career["po_GP"] > 30].copy()
    df = df.sort_values("po_delta", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Biggest Playoff Risers")
        risers = df.head(15)[["player", "PPG", "po_PPG", "po_delta", "po_GP"]].copy()
        risers.columns = ["Player", "Reg PPG", "PO PPG", "Change", "PO Games"]
        st.dataframe(risers.reset_index(drop=True), use_container_width=True)

    with col2:
        st.subheader("📉 Biggest Playoff Drops")
        drops = df.tail(15).sort_values("po_delta")[["player", "PPG", "po_PPG", "po_delta", "po_GP"]].copy()
        drops.columns = ["Player", "Reg PPG", "PO PPG", "Change", "PO Games"]
        st.dataframe(drops.reset_index(drop=True), use_container_width=True)

    chart_df = df.head(20).set_index("player")[["po_delta"]].rename(columns={"po_delta": "PPG Change"})
    st.bar_chart(chart_df, color="#ffd700")

# ════════════════════════════════
elif view == "Player Lookup":
    st.header("🔎 Player Lookup")
    st.markdown("""
    **Deep dive into any player's scoring profile.**

    Select a player to see their scoring rank, impact rank, efficiency, scoring breakdown,
    playoff performance, and a detailed explanation of why they ranked where they did.
    """)

    player = st.selectbox("Select player", sorted(career["player"].unique()))

    r = career[career["player"] == player].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        scoring_rk = int(r["scoring_rank"]) if pd.notna(r["scoring_rank"]) else "N/A"
        st.metric("Scoring Rank", f"#{scoring_rk}")
        st.metric("Career PPG", f"{r['PPG']:.1f}")
        st.metric("Games Played", f"{int(r['GP'])}")

    with col2:
        impact_rk = int(r["impact_rank"]) if pd.notna(r["impact_rank"]) else "N/A"
        st.metric("Impact Rank", f"#{impact_rk}")
        st.metric("TS%", f"{r['TS_pct']:.3f}")
        st.metric("APG", f"{r['APG']:.1f}")

    with col3:
        st.metric("Scoring Purity", f"{r['purity']:.1f}%")
        if pd.notna(r.get("po_PPG")):
            delta = r["po_PPG"] - r["PPG"]
            st.metric("Playoff PPG", f"{r['po_PPG']:.1f}", delta=f"{delta:+.1f}")
            st.metric("Playoff Games", f"{int(r['po_GP'])}")
        else:
            st.metric("Playoff PPG", "N/A")

    st.subheader("Scoring Breakdown")
    breakdown = pd.DataFrame({
        "Source": ["2-Point", "3-Point", "Free Throw"],
        "Percentage": [r["pct_2P"], r["pct_3P"], r["pct_FT"]]
    }).set_index("Source")
    st.bar_chart(breakdown, color="#00bcd4")

    st.subheader("Why this rank?")
    factors = []
    if r["PPG"] > 25: factors.append(f"✅ High volume scorer (PPG={r['PPG']:.1f})")
    elif r["PPG"] > 20: factors.append(f"✅ Solid scorer (PPG={r['PPG']:.1f})")
    else: factors.append(f"⚠️ Lower scoring volume (PPG={r['PPG']:.1f})")

    if r["TS_pct"] > 0.58: factors.append(f"✅ Elite efficiency (TS%={r['TS_pct']:.3f})")
    elif r["TS_pct"] > 0.54: factors.append(f"✅ Good efficiency (TS%={r['TS_pct']:.3f})")
    else: factors.append(f"⚠️ Below-average efficiency (TS%={r['TS_pct']:.3f})")

    if r["pct_FT"] > 28: factors.append(f"⚠️ Heavy FT reliance ({r['pct_FT']:.1f}% from FT, penalized in ranking)")
    elif r["pct_FT"] < 18: factors.append(f"✅ Low FT reliance ({r['pct_FT']:.1f}%, scores from real shots)")

    if pd.notna(r.get("po_PPG")) and r["po_GP"] > 50:
        if r["po_PPG"] > r["PPG"]:
            factors.append(f"✅ Playoff riser ({r['po_PPG']:.1f} > {r['PPG']:.1f} in {int(r['po_GP'])} games, boosted by 3x weight)")
        else:
            factors.append(f"⚠️ Playoff decline ({r['po_PPG']:.1f} < {r['PPG']:.1f} in {int(r['po_GP'])} games)")
    elif pd.notna(r.get("po_GP")) and r["po_GP"] < 50:
        factors.append(f"⚠️ Limited playoff experience ({int(r['po_GP'])} games)")

    for f in factors:
        st.markdown(f)

# ── Footer ──
st.markdown("---")
st.markdown("""
*Data sources: NBA API (1959-2026) + databallr.com (2001-2026) | 101 players (NBA 75 + modern stars)*

*All rankings are era-adjusted using scoring scarcity Z-scores, pace correction, and competition intensity.*
""")
