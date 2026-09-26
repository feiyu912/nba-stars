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
