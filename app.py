"""
NBA Player Analysis Dashboard — English / 中文

运行: streamlit run app.py

界面文案全部走 nbastars/i18n.py。选定语言后界面不再出现另一种语言的文字,
例外只有两类 (都不属于"文案"): 语言切换控件本身、以及统计缩写与球员姓名。
"""
from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from nbastars.dashboard_data import build_career_frame  # noqa: E402
from nbastars.dashboard_data import load_dimension as load_dimension_csv  # noqa: E402
from nbastars.i18n import LANGS, t  # noqa: E402

DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

st.set_page_config(page_title="NBA Player Analysis", layout="wide", page_icon="🏀")


@st.cache_data
def load_data() -> pd.DataFrame:
    return build_career_frame(DATA_DIR, RESULTS_DIR)


@st.cache_data
def load_dimension(fname: str) -> pd.DataFrame:
    """单个维度的明细表 (含图表要用的列), 走缓存避免每次交互重读磁盘"""
    return load_dimension_csv(RESULTS_DIR, fname)


career = load_data()


def fmt_rank(value) -> str:
    return f"#{int(value)}" if pd.notna(value) else t(lang, "na")


def keep_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """丢掉整列都是空的列 (空列在表里显示成一片空白)"""
    return df[[c for c in cols if df[c].notna().any()]]


# ── 语言选择 (必须先于一切文案) ──
# 语言切换控件本身用双语标注 —— 这是切换器固有的性质, 不算"混用"
lang = st.sidebar.radio("**Language / 语言**", options=list(LANGS),
                        format_func=lambda k: LANGS[k], horizontal=True)

# ── 标题 ──
st.title(t(lang, "app_title"))
st.markdown(t(lang, "app_subtitle"))
st.caption(t(lang, "app_data_note"))
st.markdown("---")

# ── 侧边栏导航 (用稳定的 key, 不依赖翻译后的文字) ──
category = st.sidebar.selectbox(
    t(lang, "sidebar_category"),
    options=["offense", "defense", "rebounding", "lookup"],
    format_func=lambda k: t(lang, f"cat_{k}"),
)

if category == "offense":
    view = st.sidebar.radio(
        t(lang, "sidebar_view"),
        options=["scoring", "impact", "playmaking", "breakdown", "playoff", "h2h"],
        format_func=lambda k: t(lang, f"view_{k}"),
    )
else:
    view = category

st.sidebar.markdown("---")
top_n = st.sidebar.slider(t(lang, "sidebar_top_n"), 10, 101, 25)

# ════════════════════════════════
if view == "scoring":
    st.header(t(lang, "scoring_header"))
    st.markdown(t(lang, "scoring_intro"))

    df = career.sort_values("scoring_rank").head(top_n).copy()
    df["rank_disp"] = df["scoring_rank"].astype(int)
    chart_df = df[["rank_disp", "player", "PPG", "TS_pct"]].copy()
    chart_df["label"] = chart_df.apply(lambda r: f"#{int(r['rank_disp'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#00bcd4").encode(
        x=alt.X("PPG:Q", title=t(lang, "col_ppg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_disp", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_disp:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("PPG:Q", title=t(lang, "col_ppg")),
                 alt.Tooltip("TS_pct:Q", title=t(lang, "col_ts"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["rank_disp", "player", "PPG", "TS_pct", "pct_FT", "purity", "GP"]].rename(columns={
        "rank_disp": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "PPG": t(lang, "col_ppg"), "TS_pct": t(lang, "col_ts"),
        "pct_FT": t(lang, "col_ft_share"), "purity": t(lang, "col_purity"),
        "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "impact":
    st.header(t(lang, "impact_header"))
    st.markdown(t(lang, "impact_intro"))

    df = career.sort_values("impact_rank").head(top_n).copy()
    df["rank_disp"] = df["impact_rank"].astype(int)
    chart_df = df[["rank_disp", "player", "PPG", "APG"]].copy()
    chart_df["label"] = chart_df.apply(lambda r: f"#{int(r['rank_disp'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#ff9800").encode(
        x=alt.X("PPG:Q", title=t(lang, "col_ppg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_disp", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_disp:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("PPG:Q", title=t(lang, "col_ppg")),
                 alt.Tooltip("APG:Q", title=t(lang, "col_apg"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["rank_disp", "player", "PPG", "APG", "TS_pct", "GP"]].rename(columns={
        "rank_disp": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "PPG": t(lang, "col_ppg"), "APG": t(lang, "col_apg"),
        "TS_pct": t(lang, "col_ts"), "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "playmaking":
    st.header(t(lang, "play_header"))
    st.markdown(t(lang, "play_intro"))

    df = career.sort_values("play_rank").head(top_n).copy()
    df["rank_disp"] = df["play_rank"].astype(int)
    chart_df = df[["rank_disp", "player", "APG", "ast_tov"]].copy()
    chart_df["label"] = chart_df.apply(lambda r: f"#{int(r['rank_disp'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#4caf50").encode(
        x=alt.X("APG:Q", title=t(lang, "col_apg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_disp", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_disp:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("APG:Q", title=t(lang, "col_apg")),
                 alt.Tooltip("ast_tov:Q", title=t(lang, "lk_ast_tov"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["rank_disp", "player", "APG", "ast_tov", "GP"]].rename(columns={
        "rank_disp": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "APG": t(lang, "col_apg"), "ast_tov": t(lang, "lk_ast_tov"),
        "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "breakdown":
    st.header(t(lang, "bd_header"))
    st.markdown(t(lang, "bd_intro"))

    df = career.sort_values("scoring_rank").head(top_n).copy()
    chart_df = df[["player", "pct_2P", "pct_3P", "pct_FT"]].set_index("player")
    chart_df.columns = [t(lang, "bd_2p"), t(lang, "bd_3p"), t(lang, "bd_ft")]
    st.bar_chart(chart_df, stack=True, color=["#2196F3", "#FF9800", "#9E9E9E"])

    cols = {"player": t(lang, "col_player"), "PPG": t(lang, "col_ppg"),
            "purity": t(lang, "col_purity"), "pct_2P": t(lang, "bd_2p"),
            "pct_3P": t(lang, "bd_3p"), "pct_FT": t(lang, "bd_ft")}
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t(lang, "bd_top_purity"))
        pure = career.sort_values("purity", ascending=False).head(10)
        st.dataframe(pure[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)
    with col2:
        st.subheader(t(lang, "bd_top_ft"))
        impure = career.sort_values("purity").head(10)
        st.dataframe(impure[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)

# ════════════════════════════════
elif view == "playoff":
    st.header(t(lang, "po_header"))
    st.markdown(t(lang, "po_intro"))

    df = career[career["po_GP"] > 30].copy().sort_values("po_delta", ascending=False)
    cols = {"player": t(lang, "col_player"), "PPG": t(lang, "po_col_reg"),
            "po_PPG": t(lang, "po_col_po"), "po_delta": t(lang, "po_col_change"),
            "po_GP": t(lang, "po_col_games")}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t(lang, "po_risers"))
        st.dataframe(df.head(15)[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)
    with col2:
        st.subheader(t(lang, "po_drops"))
        drops = df.tail(15).sort_values("po_delta")
        st.dataframe(drops[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)

    chart_df = df.head(20).set_index("player")[["po_delta"]]
    chart_df.columns = [t(lang, "po_chart")]
    st.bar_chart(chart_df, color="#ffd700")

# ════════════════════════════════
elif view == "h2h":
    st.header(t(lang, "h2h_header"))
    st.markdown(t(lang, "h2h_intro"))

    df = career[career["scoring_rank"].notna() & career["play_rank"].notna()].copy()
    compare = df[["player", "scoring_rank", "impact_rank", "play_rank",
                  "def_rank", "reb_rank", "PPG", "APG"]].sort_values("scoring_rank").head(top_n)
    # 无数据 / 样本不足的维度保持空白, 不能填 0 (会被读成"第 0 名")
    cols = {"player": t(lang, "col_player"), "scoring_rank": t(lang, "view_scoring"),
            "impact_rank": t(lang, "view_impact"), "play_rank": t(lang, "view_playmaking"),
            "def_rank": t(lang, "view_defense"), "reb_rank": t(lang, "view_rebounding"),
            "PPG": t(lang, "col_ppg"), "APG": t(lang, "col_apg")}
    st.dataframe(compare.rename(columns=cols).reset_index(drop=True),
                 use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "defense":
    st.header(t(lang, "def_header"))
    st.markdown(t(lang, "def_intro"))

    defense_data = load_dimension("defense_ranking.csv").sort_values("def_rank", na_position="last")
    df = defense_data.head(top_n).copy()

    chart_df = df[df["def_rank"].notna()][["def_rank", "player", "reg_SPG", "reg_BPG", "reg_def"]].copy()
    chart_df["rank_int"] = chart_df["def_rank"].astype(int)
    chart_df["label"] = chart_df.apply(lambda r: f"#{int(r['rank_int'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#e53935").encode(
        x=alt.X("reg_def:Q", title=t(lang, "def_chart_x")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_int", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_int:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("reg_SPG:Q", title=t(lang, "col_stl")),
                 alt.Tooltip("reg_BPG:Q", title=t(lang, "col_blk")),
                 alt.Tooltip("reg_def:Q", title=t(lang, "col_stl_blk"))]
    ).properties(height=max(len(chart_df) * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["def_rank", "player", "reg_SPG", "reg_BPG", "reg_def",
                "seasons_with_def_data", "po_GP"]].rename(columns={
        "def_rank": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "reg_SPG": t(lang, "col_stl"), "reg_BPG": t(lang, "col_blk"),
        "reg_def": t(lang, "col_stl_blk"), "seasons_with_def_data": t(lang, "col_sample"),
        "po_GP": t(lang, "col_playoff_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True,
                 height=min(len(table) * 38, 900))

    no_data = defense_data[defense_data["defense_stats_missing"] == True]["player"].tolist()  # noqa: E712
    if no_data:
        st.info(t(lang, "def_excluded_title", n=len(no_data)) + " "
                + t(lang, "def_excluded_body", names=t(lang, "name_sep").join(no_data)))
    thin = defense_data[defense_data["sample_too_small"] == True]  # noqa: E712
    if len(thin):
        sep = t(lang, "name_sep")
        names = sep.join(f"{r.player} ({int(r.seasons_with_def_data)})" for r in thin.itertuples())
        st.warning(t(lang, "def_thin_title", n=len(thin)) + " "
                   + t(lang, "def_thin_body", peak=5, names=names))

# ════════════════════════════════
elif view == "rebounding":
    st.header(t(lang, "reb_header"))
    st.markdown(t(lang, "reb_intro"))

    reb_data = load_dimension("rebounding_ranking.csv").sort_values("reb_rank")
    df = reb_data.head(top_n).copy()
    df["rank_disp"] = df["reb_rank"].astype(int)

    chart_df = df[["rank_disp", "player", "RPG", "OREB", "DREB"]].copy()
    chart_df["label"] = chart_df.apply(lambda r: f"#{int(r['rank_disp'])} {r['player']}", axis=1)
    chart = alt.Chart(chart_df).mark_bar(color="#9c27b0").encode(
        x=alt.X("RPG:Q", title=t(lang, "reb_chart_x")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_disp", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_disp:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("RPG:Q", title=t(lang, "col_rpg")),
                 alt.Tooltip("OREB:Q", title=t(lang, "col_orb")),
                 alt.Tooltip("DREB:Q", title=t(lang, "col_drb"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    show = keep_columns(df, ["rank_disp", "player", "RPG", "OREB", "DREB", "po_GP"])
    table = show.rename(columns={
        "rank_disp": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "RPG": t(lang, "col_rpg"), "OREB": t(lang, "col_orb"), "DREB": t(lang, "col_drb"),
        "po_GP": t(lang, "col_playoff_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True,
                 height=min(len(table) * 38, 900))

    no_split = reb_data[reb_data["rebound_split_missing"] == True]["player"].tolist()  # noqa: E712
    if no_split:
        st.info(t(lang, "reb_excluded_title", n=len(no_split)) + " "
                + t(lang, "reb_excluded_body", names=t(lang, "name_sep").join(no_split)))

# ════════════════════════════════
elif view == "lookup":
    st.header(t(lang, "lk_header"))
    st.markdown(t(lang, "lk_intro"))

    player = st.selectbox(t(lang, "lk_select"), sorted(career["player"].unique()))
    r = career[career["player"] == player].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.subheader(t(lang, "lk_scoring"))
        st.metric(t(lang, "lk_rank"), fmt_rank(r["scoring_rank"]))
        st.metric(t(lang, "lk_ppg"), f"{r['PPG']:.1f}")
        st.metric(t(lang, "lk_ts"), f"{r['TS_pct']:.3f}")
        st.metric(t(lang, "lk_purity"), f"{r['purity']:.1f}%")

    with col2:
        st.subheader(t(lang, "lk_impact"))
        st.metric(t(lang, "lk_rank"), fmt_rank(r["impact_rank"]))
        st.metric(t(lang, "lk_gp"), f"{int(r['GP'])}")
        if pd.notna(r.get("po_PPG")):
            delta = r["po_PPG"] - r["PPG"]
            st.metric(t(lang, "lk_po_ppg"), f"{r['po_PPG']:.1f}", delta=f"{delta:+.1f}")
        else:
            st.metric(t(lang, "lk_po_ppg"), t(lang, "na"))

    with col3:
        st.subheader(t(lang, "lk_playmaking"))
        st.metric(t(lang, "lk_rank"), fmt_rank(r["play_rank"]))
        st.metric(t(lang, "lk_apg"), f"{r['APG']:.1f}")
        st.metric(t(lang, "lk_ast_tov"),
                  f"{r['ast_tov']:.2f}" if pd.notna(r["ast_tov"]) else t(lang, "na"))

    with col4:
        st.subheader(t(lang, "lk_def_reb"))
        st.metric(t(lang, "lk_def_rank"), fmt_rank(r.get("def_rank")))
        st.metric(t(lang, "lk_reb_rank"), fmt_rank(r.get("reb_rank")))
        if pd.notna(r.get("reb_RPG")):
            st.metric(t(lang, "lk_rpg"), f"{r['reb_RPG']:.1f}")
        if pd.notna(r.get("reb_OREB")) and pd.notna(r.get("reb_DREB")):
            st.metric(t(lang, "lk_orb_drb"), f"{r['reb_OREB']:.1f} / {r['reb_DREB']:.1f}")

    st.subheader(t(lang, "lk_breakdown"))
    breakdown = pd.DataFrame({
        "source": [t(lang, "lk_src_2p"), t(lang, "lk_src_3p"), t(lang, "lk_src_ft")],
        "pct": [r["pct_2P"], r["pct_3P"], r["pct_FT"]],
    }).set_index("source")
    st.bar_chart(breakdown, color="#00bcd4")

    st.subheader(t(lang, "lk_analysis"))
    factors = []
    if r["PPG"] > 25:
        factors.append(t(lang, "f_high_volume", ppg=r["PPG"]))
    elif r["PPG"] > 20:
        factors.append(t(lang, "f_solid_scorer", ppg=r["PPG"]))
    else:
        factors.append(t(lang, "f_low_volume", ppg=r["PPG"]))

    if r["TS_pct"] > 0.58:
        factors.append(t(lang, "f_elite_eff", ts=r["TS_pct"]))
    elif r["TS_pct"] > 0.54:
        factors.append(t(lang, "f_good_eff", ts=r["TS_pct"]))
    else:
        factors.append(t(lang, "f_low_eff", ts=r["TS_pct"]))

    if r["pct_FT"] > 28:
        factors.append(t(lang, "f_heavy_ft", ft=r["pct_FT"]))
    elif r["pct_FT"] < 18:
        factors.append(t(lang, "f_low_ft", ft=r["pct_FT"]))

    if r["APG"] > 7:
        factors.append(t(lang, "f_elite_playmaker", apg=r["APG"]))
    elif r["APG"] > 4:
        factors.append(t(lang, "f_good_playmaker", apg=r["APG"]))
    else:
        factors.append(t(lang, "f_limited_playmaking", apg=r["APG"]))

    if pd.isna(r["ast_tov"]):
        factors.append(t(lang, "f_no_tov"))
    elif r["ast_tov"] > 2.5:
        factors.append(t(lang, "f_excellent_decision", ratio=r["ast_tov"]))
    elif r["ast_tov"] < 1.5:
        factors.append(t(lang, "f_turnover_prone", ratio=r["ast_tov"]))

    if pd.notna(r.get("po_PPG")) and r["po_GP"] > 50:
        if r["po_PPG"] > r["PPG"]:
            factors.append(t(lang, "f_po_riser", po=r["po_PPG"], reg=r["PPG"],
                             games=int(r["po_GP"])))
        else:
            factors.append(t(lang, "f_po_decline", po=r["po_PPG"], reg=r["PPG"],
                             games=int(r["po_GP"])))
    elif pd.notna(r.get("po_GP")) and r["po_GP"] < 50:
        factors.append(t(lang, "f_limited_po", games=int(r["po_GP"])))

    for f in factors:
        st.markdown(f)

# ── 页脚 ──
st.markdown("---")
st.markdown(t(lang, "footer_sources"))
st.markdown(t(lang, "footer_notes"))
