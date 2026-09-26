"""
NBA Player Analysis Dashboard — English / 中文

运行: streamlit run app.py

两条硬约束:
  1. 界面文案全部走 nbastars/i18n.py。选定语言后不再出现另一种语言的文字
     (例外只有语言切换控件本身、球员姓名、以及统计记号 —— 见 tests/test_i18n.py 的允许清单)。
  2. 缺失值一律显示 N/A, 不做估算填充。

信息架构按"维度"分组, 每个维度给出数据真正支持的细分:
  进攻: 得分排名 / 得分结构 / 进攻影响力 / 组织能力
  防守: 防守排名 / 抢断与盖帽 / 防守影响力
  篮板: 篮板排名 / 进攻与防守篮板
  横向对比: 季后赛表现 / 跨维度对比   (与单一维度无关, 所以单独一类)
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

# 语言要先于一切文案, 但 set_page_config 必须是第一个 Streamlit 命令。
# 用上一次运行的会话状态取语言: 首次渲染用默认值, 切换语言后标签页标题跟着变。
_DEFAULT_LANG = st.session_state.get("lang", "en")
st.set_page_config(page_title=t(_DEFAULT_LANG, "page_title"), layout="wide", page_icon="🏀")


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


def rank_label(prefix: str, df: pd.DataFrame) -> pd.Series:
    """给图表用的 "#名次 球员名" 标签"""
    return df.apply(
        lambda r: f"#{int(r[f'{prefix}_rank'])} {r['player']}" if pd.notna(r[f"{prefix}_rank"])
        else t(lang, "na"), axis=1)


# ── 语言选择 ──
lang = st.sidebar.radio("**Language / 语言**", options=list(LANGS), key="lang",
                        format_func=lambda k: LANGS[k], horizontal=True)

# ── 标题 ──
st.title(t(lang, "app_title"))
st.markdown(t(lang, "app_subtitle"))
st.caption(t(lang, "app_data_note"))
st.markdown("---")

# ── 侧边栏导航: 分类 → 视图 (用稳定的 key, 不依赖翻译后的文字) ──
VIEWS_BY_CATEGORY = {
    "offense": ["scoring", "breakdown", "impact", "playmaking"],
    "defense": ["defense", "def_split", "def_impact"],
    "rebounding": ["rebounding", "reb_split"],
    "compare": ["playoff", "h2h"],
    "lookup": [],
}

# 侧边栏控件的选项标签随语言变化, 所以这里直接把翻译后的文字当选项, 并且:
#   1. 控件 key 里带上语言 —— 换语言就是换一个控件, 标签不会残留成上一种语言
#      (用 format_func + 固定 key 试过: 换语言后下拉框仍显示英文)
#   2. 另存一份"当前选择", 换语言时用 index= 还原, 免得一切换就被重置回第一项
def _kept_index(option_keys: list[str], state_key: str) -> int:
    prev = st.session_state.get(state_key)
    return option_keys.index(prev) if prev in option_keys else 0


CATEGORY_KEYS = list(VIEWS_BY_CATEGORY)
cat_labels = [t(lang, f"cat_{k}") for k in CATEGORY_KEYS]
cat_choice = st.sidebar.selectbox(
    t(lang, "sidebar_category"), options=cat_labels,
    index=_kept_index(CATEGORY_KEYS, "category_key"), key=f"category_{lang}",
)
category = CATEGORY_KEYS[cat_labels.index(cat_choice)]
st.session_state["category_key"] = category

sub_views = VIEWS_BY_CATEGORY[category]
if sub_views:
    view_labels = [t(lang, f"view_{k}") for k in sub_views]
    view_choice = st.sidebar.radio(
        t(lang, "sidebar_view"), options=view_labels,
        index=_kept_index(sub_views, "view_key"), key=f"view_{lang}_{category}",
    )
    view = sub_views[view_labels.index(view_choice)]
    st.session_state["view_key"] = view
else:
    view = "lookup"

st.sidebar.markdown("---")
top_n = st.sidebar.slider(
    t(lang, "sidebar_top_n"), 10, 101,
    st.session_state.get("top_n_value", 25), key=f"top_n_{lang}",
)
st.session_state["top_n_value"] = top_n

# ════════════════════════════════
if view == "scoring":
    st.header(t(lang, "scoring_header"))
    st.markdown(t(lang, "scoring_intro"))

    df = career.sort_values("scoring_rank").head(top_n).copy()
    df["rank_int"] = df["scoring_rank"].astype(int)
    df["label"] = rank_label("scoring", df)
    chart = alt.Chart(df).mark_bar(color="#00bcd4").encode(
        x=alt.X("PPG:Q", title=t(lang, "col_ppg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_int", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_int:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("PPG:Q", title=t(lang, "col_ppg")),
                 alt.Tooltip("TS_pct:Q", title=t(lang, "col_ts"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["rank_int", "player", "PPG", "TS_pct", "pct_FT", "purity", "GP"]].rename(columns={
        "rank_int": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "PPG": t(lang, "col_ppg"), "TS_pct": t(lang, "col_ts"),
        "pct_FT": t(lang, "col_ft_share"), "purity": t(lang, "col_purity"),
        "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "breakdown":
    st.header(t(lang, "bd_header"))
    st.markdown(t(lang, "bd_intro"))

    df = career.sort_values("scoring_rank").head(top_n).copy()
    long_df = df[["player", "pct_2P", "pct_3P", "pct_FT"]].melt(
        id_vars="player", var_name="src", value_name="pct")
    long_df["src"] = long_df["src"].map({"pct_2P": t(lang, "bd_2p"),
                                         "pct_3P": t(lang, "bd_3p"),
                                         "pct_FT": t(lang, "bd_ft")})
    chart = alt.Chart(long_df).mark_bar().encode(
        x=alt.X("player:N", title="", sort=alt.EncodingSortField(field="player", order="ascending")),
        y=alt.Y("pct:Q", title=t(lang, "bd_share"), stack="zero"),
        color=alt.Color("src:N", title=t(lang, "lk_source"),
                        scale=alt.Scale(domain=[t(lang, "bd_2p"), t(lang, "bd_3p"), t(lang, "bd_ft")],
                                        range=["#2196F3", "#FF9800", "#9E9E9E"])),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("src:N", title=t(lang, "lk_source")),
                 alt.Tooltip("pct:Q", title=t(lang, "bd_share"))]
    ).properties(height=500)
    st.altair_chart(chart, use_container_width=True)

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
elif view == "impact":
    st.header(t(lang, "impact_header"))
    st.markdown(t(lang, "impact_intro"))

    df = career.sort_values("impact_rank").head(top_n).copy()
    df["rank_int"] = df["impact_rank"].astype(int)
    df["label"] = rank_label("impact", df)
    chart = alt.Chart(df).mark_bar(color="#ff9800").encode(
        x=alt.X("PPG:Q", title=t(lang, "col_ppg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_int", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_int:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("PPG:Q", title=t(lang, "col_ppg")),
                 alt.Tooltip("APG:Q", title=t(lang, "col_apg"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    table = df[["rank_int", "player", "PPG", "APG", "TS_pct", "GP"]].rename(columns={
        "rank_int": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "PPG": t(lang, "col_ppg"), "APG": t(lang, "col_apg"),
        "TS_pct": t(lang, "col_ts"), "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

# ════════════════════════════════
elif view == "playmaking":
    st.header(t(lang, "play_header"))
    st.markdown(t(lang, "play_intro"))

    df = career.sort_values("play_rank").head(top_n).copy()
    df["rank_int"] = df["play_rank"].astype(int)
    df["label"] = rank_label("play", df)
    chart = alt.Chart(df).mark_bar(color="#4caf50").encode(
        x=alt.X("APG:Q", title=t(lang, "col_apg")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_int", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_int:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("APG:Q", title=t(lang, "col_apg")),
                 alt.Tooltip("ast_tov:Q", title=t(lang, "lk_ast_tov"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    # 助失比在 1977-78 之前是估算值, 必须让人看见 —— 组织指数整个乘在这个估算值上
    pm = load_dimension("playmaking_ranking.csv")[["player", "TOV_imputed_share"]]
    df = df.merge(pm, on="player", how="left")
    df["estimated"] = (df["TOV_imputed_share"].fillna(0) > 0.5).map({True: "✓", False: ""})

    table = df[["rank_int", "player", "APG", "ast_tov", "estimated", "GP"]].rename(columns={
        "rank_int": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "APG": t(lang, "col_apg"), "ast_tov": t(lang, "lk_ast_tov"),
        "estimated": t(lang, "col_estimated"), "GP": t(lang, "col_gp"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True, height=min(top_n * 38, 900))

    affected = df[(df["TOV_imputed_share"].fillna(0) > 0.5)]["player"].tolist()
    if affected:
        st.warning(t(lang, "play_tov_note", names=t(lang, "name_sep").join(affected)))

# ════════════════════════════════
elif view == "defense":
    st.header(t(lang, "def_header"))
    st.markdown(t(lang, "def_intro"))

    defense_data = load_dimension("defense_ranking.csv").sort_values("def_rank", na_position="last")
    df = defense_data.head(top_n).copy()

    chart_df = df[df["def_rank"].notna()].copy()
    chart_df["rank_int"] = chart_df["def_rank"].astype(int)
    chart_df["label"] = rank_label("def", chart_df)
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
        names = sep.join(t(lang, "thin_name_item", name=r.player, n=int(r.seasons_with_def_data))
                         for r in thin.itertuples())
        st.warning(t(lang, "def_thin_title", n=len(thin)) + " "
                   + t(lang, "def_thin_body", peak=5, names=names))

# ════════════════════════════════
elif view == "def_split":
    st.header(t(lang, "def_split_header"))
    st.markdown(t(lang, "def_split_intro"))

    d = load_dimension("defense_ranking.csv")

    blocks = d[d["blk_rank"].notna()].sort_values("blk_rank").head(top_n)
    steals = d[d["stl_rank"].notna()].sort_values("stl_rank").head(top_n)
    cols = {"stl_rank": t(lang, "col_rank"), "player": t(lang, "col_player"),
            "reg_SPG": t(lang, "col_stl"), "reg_BPG": t(lang, "col_blk")}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t(lang, "def_split_stl"))
        st.dataframe(steals[["stl_rank", "player", "reg_SPG"]].rename(columns=cols)
                     .reset_index(drop=True), use_container_width=True,
                     height=min(top_n * 38, 900))
    with col2:
        st.subheader(t(lang, "def_split_blk"))
        st.dataframe(blocks[["blk_rank", "player", "reg_BPG"]].rename(columns=cols)
                     .reset_index(drop=True), use_container_width=True,
                     height=min(top_n * 38, 900))

    no_data = d[d["defense_stats_missing"] == True]["player"].tolist()  # noqa: E712
    if no_data:
        st.info(t(lang, "def_excluded_title", n=len(no_data)) + " "
                + t(lang, "def_excluded_body", names=t(lang, "name_sep").join(no_data)))

# ════════════════════════════════
elif view == "def_impact":
    st.header(t(lang, "def_impact_header"))
    st.markdown(t(lang, "def_impact_intro"))

    d = load_dimension("defense_ranking.csv")
    ranked = d[d["def_impact_rank"].notna()].sort_values("def_impact_rank").head(top_n)
    st.caption(t(lang, "def_impact_model", n=53, r2=0.359, rho=0.667))

    table = ranked[["def_impact_rank", "player", "def_impact_score", "d_dpm",
                    "reg_SPG", "reg_BPG"]].rename(columns={
        "def_impact_rank": t(lang, "col_rank"), "player": t(lang, "col_player"),
        "def_impact_score": t(lang, "imp_predicted"), "d_dpm": t(lang, "imp_actual"),
        "reg_SPG": t(lang, "col_stl"), "reg_BPG": t(lang, "col_blk"),
    })
    st.dataframe(table.reset_index(drop=True), use_container_width=True,
                 height=min(len(table) * 38, 900))

    no_data = d[d["defense_stats_missing"] == True]["player"].tolist()  # noqa: E712
    if no_data:
        st.info(t(lang, "def_excluded_title", n=len(no_data)) + " "
                + t(lang, "def_excluded_body", names=t(lang, "name_sep").join(no_data)))

# ════════════════════════════════
elif view == "rebounding":
    st.header(t(lang, "reb_header"))
    st.markdown(t(lang, "reb_intro"))

    reb_data = load_dimension("rebounding_ranking.csv").sort_values("reb_rank")
    df = reb_data.head(top_n).copy()
    df["rank_int"] = df["reb_rank"].astype(int)
    df["label"] = rank_label("reb", df)
    chart = alt.Chart(df).mark_bar(color="#9c27b0").encode(
        x=alt.X("RPG:Q", title=t(lang, "reb_chart_x")),
        y=alt.Y("label:N", sort=alt.EncodingSortField(field="rank_int", order="ascending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip("rank_int:Q", title=t(lang, "col_rank")),
                 alt.Tooltip("RPG:Q", title=t(lang, "col_rpg")),
                 alt.Tooltip("OREB:Q", title=t(lang, "col_orb")),
                 alt.Tooltip("DREB:Q", title=t(lang, "col_drb"))]
    ).properties(height=max(top_n * 28, 400))
    st.altair_chart(chart, use_container_width=True)

    show = keep_columns(df, ["rank_int", "player", "RPG", "OREB", "DREB", "po_GP"])
    table = show.rename(columns={
        "rank_int": t(lang, "col_rank"), "player": t(lang, "col_player"),
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
elif view == "reb_split":
    st.header(t(lang, "reb_split_header"))
    st.markdown(t(lang, "reb_split_intro"))

    r = load_dimension("rebounding_ranking.csv")
    orb = r[r["oreb_rank"].notna()].sort_values("oreb_rank").head(top_n)
    drb = r[r["dreb_rank"].notna()].sort_values("dreb_rank").head(top_n)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t(lang, "reb_split_orb"))
        t1 = orb[["oreb_rank", "player", "peak_OREB"]].rename(columns={
            "oreb_rank": t(lang, "col_rank"), "player": t(lang, "col_player"),
            "peak_OREB": t(lang, "col_peak")})
        st.dataframe(t1.reset_index(drop=True), use_container_width=True,
                     height=min(top_n * 38, 900))
    with col2:
        st.subheader(t(lang, "reb_split_drb"))
        t2 = drb[["dreb_rank", "player", "peak_DREB"]].rename(columns={
            "dreb_rank": t(lang, "col_rank"), "player": t(lang, "col_player"),
            "peak_DREB": t(lang, "col_peak")})
        st.dataframe(t2.reset_index(drop=True), use_container_width=True,
                     height=min(top_n * 38, 900))

    no_split = r[r["rebound_split_missing"] == True]["player"].tolist()  # noqa: E712
    if no_split:
        st.info(t(lang, "reb_excluded_title", n=len(no_split)) + " "
                + t(lang, "reb_excluded_body", names=t(lang, "name_sep").join(no_split)))

# ════════════════════════════════
elif view == "playoff":
    st.header(t(lang, "po_header"))
    st.markdown(t(lang, "po_intro"))

    metric = st.radio(t(lang, "po_metric"), options=["scoring", "rebounds", "assists"],
                      horizontal=True,
                      format_func=lambda k: t(lang, f"po_metric_{k}"))
    reg_col = {"scoring": "PPG", "rebounds": "reb_RPG", "assists": "APG"}[metric]
    po_col = {"scoring": "po_PPG", "rebounds": "po_RPG", "assists": "po_APG"}[metric]
    delta_col = {"scoring": "po_delta_ppg", "rebounds": "po_delta_rpg",
                 "assists": "po_delta_apg"}[metric]
    metric_label = t(lang, f"po_metric_{metric}")

    df = career[career["po_GP"] > 30].dropna(subset=[delta_col]).copy()
    df = df.sort_values(delta_col, ascending=False)
    cols = {"player": t(lang, "col_player"), reg_col: t(lang, "po_col_reg"),
            po_col: t(lang, "po_col_po"), delta_col: t(lang, "po_col_change"),
            "po_GP": t(lang, "po_col_games")}

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t(lang, "po_risers"))
        st.dataframe(df.head(15)[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)
    with col2:
        st.subheader(t(lang, "po_drops"))
        drops = df.tail(15).sort_values(delta_col)
        st.dataframe(drops[list(cols)].rename(columns=cols).reset_index(drop=True),
                     use_container_width=True)

    top20 = df.head(20)[["player", delta_col]].copy()
    chart = alt.Chart(top20).mark_bar(color="#ffd700").encode(
        x=alt.X(f"{delta_col}:Q", title=t(lang, "po_chart", metric=metric_label)),
        y=alt.Y("player:N", sort=alt.EncodingSortField(field=delta_col, order="descending"), title=""),
        tooltip=[alt.Tooltip("player:N", title=t(lang, "col_player")),
                 alt.Tooltip(f"{delta_col}:Q", title=t(lang, "po_col_change"))]
    ).properties(height=max(len(top20) * 26, 400))
    st.altair_chart(chart, use_container_width=True)

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
    src = pd.DataFrame({
        "src": [t(lang, "lk_src_2p"), t(lang, "lk_src_3p"), t(lang, "lk_src_ft")],
        "pct": [r["pct_2P"], r["pct_3P"], r["pct_FT"]],
    })
    breakdown_chart = alt.Chart(src).mark_bar(color="#00bcd4").encode(
        y=alt.Y("src:N", title="", sort=None),
        x=alt.X("pct:Q", title=t(lang, "bd_share")),
        tooltip=[alt.Tooltip("src:N", title=t(lang, "lk_source")),
                 alt.Tooltip("pct:Q", title=t(lang, "bd_share"))]
    ).properties(height=180)
    st.altair_chart(breakdown_chart, use_container_width=True)

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
