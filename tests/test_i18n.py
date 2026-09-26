"""界面文案测试: 两种语言的键必须对齐, 中文里不能混进英文。"""
from __future__ import annotations

import re

import pytest

from nbastars.i18n import STRINGS, check_complete, t

# 中文文案里允许出现的拉丁字符: 专有名词、外链来源、文件名、统计记号
# 允许清单是显式的 —— 新增例外必须写进这里, 不能靠"看起来还行"
ALLOWED_LATIN_IN_ZH = {
    "NBA", "NBA.com", "O-DPM", "ESPN", "Basketball-Reference",
    "Z", "N",                          # 数学变量: Z 分数、前 N 名
    "D-DPM",                           # 第三方防守指标名, 与 O-DPM 同类
    "R", "Spearman",                   # 统计记号与专有名词 (R²、Spearman 秩相关)
    "Stockton", "Westbrook", "Oscar", "Robertson",   # 球衣姓名: 数据表里就是拉丁字母, 正文保持一致
    "scripts", "verify", "py",        # 脚本路径
}

LATIN_TOKEN = re.compile(r"[A-Za-z][A-Za-z.\-]*")


def test_language_keys_are_aligned():
    assert check_complete() == [], "两种语言的文案键不一致"


def test_every_key_exists_in_both_languages():
    for key in STRINGS["en"]:
        for lang in ("en", "zh"):
            assert t(lang, key), f"{lang} 的 {key} 是空的"


def test_missing_key_raises_instead_of_falling_back():
    """取不到文案时必须报错 —— 静默回退到另一种语言就是"混用"的来源"""
    with pytest.raises(KeyError):
        t("zh", "definitely_not_a_key")


PLACEHOLDER = re.compile(r"\{[^}]*\}")


def test_chinese_strings_have_no_stray_english():
    """占位符 {names} 之类先剥掉, 剩下还出现拉丁单词就算混用"""
    offenders: list[str] = []
    for key, text in STRINGS["zh"].items():
        body = PLACEHOLDER.sub("", text)
        stray = {tok for tok in LATIN_TOKEN.findall(body)} - ALLOWED_LATIN_IN_ZH
        if stray:
            offenders.append(f"{key}: {sorted(stray)}")
    assert not offenders, "中文文案里混入了英文: " + "; ".join(offenders)


def test_english_strings_have_no_stray_chinese():
    cjk = re.compile(r"[\u4e00-\u9fff]")
    offenders = [k for k, v in STRINGS["en"].items() if cjk.search(v)]
    assert not offenders, f"英文文案里混入了中文: {offenders}"


def test_placeholders_match_between_languages():
    """同一个键在两边的占位符必须一致, 否则切换语言时会 KeyError"""
    ph = re.compile(r"\{(\w+)")
    for key, en in STRINGS["en"].items():
        zh = STRINGS["zh"][key]
        assert set(ph.findall(en)) == set(ph.findall(zh)), f"{key} 的占位符不一致"


def test_lang_switch_renders_both():
    """抽查几个带占位符的文案, 两种语言都要能正常格式化"""
    assert "Michael Jordan" in t("zh", "def_excluded_body", names="Michael Jordan")
    assert "8" in t("en", "def_thin_title", n=8)
    assert t("en", "na") != t("zh", "na")


# ══════════════════════════════════════════════
# 防止"文案漏走 i18n"与"文案表腐化"的两道闸
# ══════════════════════════════════════════════
import ast  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402

APP = Path(__file__).resolve().parent.parent / "app.py"

# 会渲染到界面上的 Streamlit 函数 —— 第一个参数必须是 t(...) 的结果
RENDER_FUNCS = {
    "title", "header", "subheader", "markdown", "caption", "info", "warning", "error",
    "success", "metric", "dataframe", "data_table", "selectbox", "radio", "slider",
    "checkbox", "button", "text_input", "bar_chart", "line_chart", "area_chart",
    "altair_chart", "expander", "tabs", "table",
}
# 语言切换控件本身必须同时显示两种语言, 这是唯一豁免的字面量
ALLOWED_LITERALS = {"**Language / 语言**"}


def _literal_ui_strings(source: str) -> list[str]:
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        root = node.func.value
        # st.X(...) 或 st.sidebar.X(...)
        if isinstance(root, ast.Attribute) and isinstance(root.value, ast.Name):
            root = root.value
        if not (isinstance(root, ast.Name) and root.id == "st"):
            continue
        if node.func.attr not in RENDER_FUNCS or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            has_words = re.search(r"[A-Za-z\u4e00-\u9fff]", first.value)
            if has_words and first.value not in ALLOWED_LITERALS:
                offenders.append(f"app.py:{node.lineno} st.{node.func.attr}({first.value[:40]!r})")
    return offenders


def test_no_hardcoded_ui_text_in_app():
    """界面上出现的文案必须来自 i18n —— 正则/人眼都会漏, 所以用语法树查"""
    assert not _literal_ui_strings(APP.read_text()), (
        "发现硬编码的界面文案: " + "; ".join(_literal_ui_strings(APP.read_text()))
    )


# app.py 用 f"cat_{k}" 这类动态键拼出来的文案族
DYNAMIC_KEYS = (
    [f"cat_{c}" for c in ["offense", "defense", "rebounding", "compare", "lookup"]]
    + [f"view_{v}" for v in ["scoring", "breakdown", "impact", "playmaking", "defense",
                             "def_split", "def_impact", "rebounding", "reb_split",
                             "playoff", "h2h"]]
    + [f"po_metric_{m}" for m in ["scoring", "rebounds", "assists"]]
)


def test_no_dead_i18n_keys():
    """文案表里不该留没人用的键 —— 曾经留下过 lang_label / scoring_chart_x"""
    root = APP.parent
    corpus = "\n".join(
        p.read_text()
        for p in [APP, *sorted((root / "nbastars").glob("*.py")), *sorted((root / "tests").glob("*.py"))]
    )
    used = set(re.findall(r'"([a-z0-9_]+)"', corpus)) | set(DYNAMIC_KEYS)
    dead = sorted(set(STRINGS["en"]) - used)
    assert not dead, f"这些文案键已无人使用: {dead}"


def test_every_key_referenced_by_app_is_defined():
    """反过来也要查: app.py 里 t(lang, "xxx") 引用的键必须存在。

    实际踩过: 新写的防守影响力视图引用了 imp_predicted / imp_actual, 但忘了往文案表里加,
    测试全绿而界面直接 KeyError 崩掉。
    """
    source = APP.read_text()
    referenced = set(re.findall(r't\(lang,\s*"([a-z0-9_]+)"', source)) | set(DYNAMIC_KEYS)
    missing = sorted(referenced - set(STRINGS["en"]) - set(STRINGS["zh"]))
    assert not missing, f"app.py 引用了不存在的文案键: {missing}"
