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

# 第一参数就是文案的函数
TEXT_FIRST_FUNCS = {
    "title", "header", "subheader", "markdown", "caption", "info", "warning", "error",
    "success", "metric", "selectbox", "radio", "slider", "checkbox", "button",
    "text_input", "expander", "tabs", "table",
}
# 这些关键字参数是给人看的, 出现在任何 st.* 调用里都要查 (例如 st.image(caption=...))
TEXT_KEYWORDS = {"caption", "help", "label", "placeholder"}
ALLOWED_LITERALS = {"**Language / 语言**"}
WORDLIKE = re.compile(r"[A-Za-z]{3,}|[\u4e00-\u9fff]")


def _has_words(node: ast.AST) -> bool:
    """判断一个表达式节点里有没有"像文案的东西": 字面量、f-string 的固定部分、字符串拼接"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(WORDLIKE.search(node.value))
    if isinstance(node, ast.JoinedStr):                       # f"Hardcoded {x}"
        return any(_has_words(v) for v in node.values)
    if isinstance(node, ast.FormattedValue):
        return False                                          # f"{x}" 里的变量不算文案
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _has_words(node.left) or _has_words(node.right)
    return False


def _literal_ui_strings(source: str) -> list[str]:
    """扫出所有没走 i18n 的界面文案。

    只查第一个字面量会被绕过 (子智能体验证过): f-string、字符串拼接、
    caption= 之类的关键字参数都漏。这里把三类都覆盖。
    """
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
        fn = node.func.attr

        checks: list[tuple[str, ast.AST]] = []
        if fn in TEXT_FIRST_FUNCS and node.args:
            checks.append(("arg0", node.args[0]))
        checks += [(f"{kw.arg}=", kw.value) for kw in node.keywords
                   if kw.arg in TEXT_KEYWORDS]

        for where, expr in checks:
            if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
                if expr.value in ALLOWED_LITERALS:
                    continue
            if _has_words(expr):
                offenders.append(f"app.py:{node.lineno} st.{fn}({where}) — {ast.unparse(expr)[:45]}")
    return offenders


def test_no_hardcoded_ui_text_in_app():
    """界面上出现的文案必须来自 i18n —— 正则/人眼都会漏, 所以用语法树查"""
    source = APP.read_text()
    offenders = _literal_ui_strings(source)
    assert not offenders, "发现硬编码的界面文案: " + "; ".join(offenders)


def test_hardcoded_guard_catches_evasions():
    """闸门必须真的拦得住 —— 这三种写法是子智能体用来绕过旧版闸门的"""
    evasions = [
        'st.header(f"Hardcoded {x}")',                    # f-string
        'st.markdown("Hard" + "coded")',                   # 拼接
        'st.image("i.png", caption="Hardcoded caption")',  # 关键字参数
        'st.info("plain literal")',                        # 直接字面量
    ]
    for src in evasions:
        assert _literal_ui_strings(src), f"这种写法绕过了闸门: {src}"
    # 不该误报的写法
    for src in ['st.dataframe(df)', 'st.metric(t(lang, "k"), f"{v:.1f}")',
                'st.altair_chart(chart, width="stretch")', 'st.markdown("---")']:
        assert not _literal_ui_strings(src), f"误报了: {src}"


# app.py 用 f"cat_{k}" 这类动态键拼出来的文案族
DYNAMIC_KEYS = (
    [f"cat_{c}" for c in ["offense", "defense", "rebounding", "compare", "lookup"]]
    + [f"view_{v}" for v in ["scoring", "breakdown", "impact", "playmaking", "defense",
                             "def_split", "def_impact", "rebounding", "reb_split",
                             "playoff", "h2h"]]
    + [f"po_metric_{m}" for m in ["scoring", "rebounds", "assists"]]
)


def _usage_corpus() -> str:
    """统计"谁用了哪些文案键"时的语料。

    必须排除 i18n.py 自己 —— 否则每个键的定义本身就算"被使用", 闸门形同虚设
    (子智能体证明过: 那时删掉 app.py 里全部 t(lang,"def_header") 调用, 测试照样绿)。
    """
    root = APP.parent
    files = [APP, *sorted((root / "nbastars").glob("*.py")), *sorted((root / "tests").glob("*.py"))]
    files = [f for f in files if f.name != "i18n.py"]
    return "\n".join(f.read_text() for f in files)


def test_no_dead_i18n_keys():
    """文案表里不该留没人用的键 —— 曾经留下过 lang_label / scoring_chart_x"""
    used = set(re.findall(r'"([a-z0-9_]+)"', _usage_corpus())) | set(DYNAMIC_KEYS)
    dead = sorted(set(STRINGS["en"]) - used)
    assert not dead, f"这些文案键已无人使用: {dead}"


def test_dead_key_guard_catches_unused_key():
    """把曾经真实存在的死键放回文案表, 闸门必须报出来。

    注意键名要用拼接写 —— 直接写成字面量的话, 这句断言本身就会出现在语料里,
    等于自己宣称"有人在用", 闸门就又失效了。
    """
    dead_key = "col_stl" + "_rank"          # 曾经真的存在过, 且没人引用
    assert dead_key not in _usage_corpus(), "测试代码污染了语料"
    STRINGS["en"][dead_key] = "Steals rank"
    try:
        used = set(re.findall(r'"([a-z0-9_]+)"', _usage_corpus())) | set(DYNAMIC_KEYS)
        dead = sorted(set(STRINGS["en"]) - used)
        assert dead_key in dead, "闸门没有识别出没人用的键"
    finally:
        del STRINGS["en"][dead_key]


def test_every_key_referenced_by_app_is_defined():
    r"""反过来也要查: app.py 里 t(...) 引用的键必须存在。

    实际踩过: 新写的防守影响力视图引用了 imp_predicted / imp_actual, 但忘了往文案表里加,
    测试全绿而界面直接 KeyError 崩掉。
    语言参数不一定是 lang (set_page_config 那行用的是 _DEFAULT_LANG), 所以用 \w+ 匹配。
    """
    source = APP.read_text()
    referenced = set(re.findall(r't\(\s*\w+\s*,\s*"([a-z0-9_]+)"', source)) | set(DYNAMIC_KEYS)
    missing = sorted(referenced - set(STRINGS["en"]) - set(STRINGS["zh"]))
    assert not missing, f"app.py 引用了不存在的文案键: {missing}"


def test_reverse_guard_sees_non_lang_first_argument():
    """_DEFAULT_LANG 这种写法的引用也要被扫到"""
    src = 'st.set_page_config(page_title=t(_DEFAULT_LANG, "page_title_typo"))'
    ref = set(re.findall(r't\(\s*\w+\s*,\s*"([a-z0-9_]+)"', src))
    assert ref == {"page_title_typo"}, "反向闸门漏掉了非 lang 命名的语言参数"
