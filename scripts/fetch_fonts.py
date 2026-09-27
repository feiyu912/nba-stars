"""下载并自托管网页字体 (Inter + JetBrains Mono)。

为什么要自托管而不是引 CDN: 站点要能离线打开、不依赖第三方可用性, 也不把访问者
的请求暴露给 Google。两个字体都是 SIL OFL 许可, 允许再分发 (下载时会一并存下许可证)。

做法: 用现代 UA 请求 Google Fonts 的 CSS (这样返回 woff2), 把里面引用的字体文件
下载到 docs/assets/fonts/, 再把 CSS 里的 URL 改写成本地相对路径。

用法: python scripts/fetch_fonts.py
"""
from __future__ import annotations

import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "docs" / "assets" / "fonts"
CSS_OUT = ROOT / "docs" / "assets" / "fonts.css"

# 现代浏览器 UA —— 不带它 Google 会返回旧格式 (ttf), 体积大很多
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

FAMILIES = [
    ("Inter", "Inter:wght@400;500;600;700;800"),
    ("JetBrains Mono", "JetBrains+Mono:wght@400;500;700"),
]
LICENSES = ["https://raw.githubusercontent.com/rsms/inter/master/LICENSE.txt",
            "https://raw.githubusercontent.com/JetBrains/JetBrainsMono/master/OFL.txt"]


def main() -> int:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    total = 0

    for label, spec in FAMILIES:
        url = f"https://fonts.googleapis.com/css2?family={spec}&display=swap"
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        css = r.text
        urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)))
        print(f"{label}: {len(urls)} 个字体文件")
        for u in urls:
            name = f"{label.replace(' ', '')}-" + u.rsplit("/", 1)[-1]
            target = FONT_DIR / name
            if not target.exists():
                fr = requests.get(u, headers={"User-Agent": UA}, timeout=60)
                fr.raise_for_status()
                target.write_bytes(fr.content)
            total += target.stat().st_size
            css = css.replace(u, f"fonts/{name}")
        blocks.append(f"/* ── {label} (SIL OFL) ── */\n{css.strip()}")

    CSS_OUT.write_text(
        "/* 自动生成, 勿手改: python scripts/fetch_fonts.py\n"
        "   Inter / JetBrains Mono, 均为 SIL OFL 许可, 见 fonts/OFL-*.txt */\n\n"
        + "\n\n".join(blocks) + "\n")

    lic_dir = FONT_DIR
    for u in LICENSES:
        try:
            lr = requests.get(u, timeout=30)
            if lr.status_code == 200:
                name = "OFL-Inter.txt" if "inter" in u.lower() else "OFL-JetBrainsMono.txt"
                (lic_dir / name).write_bytes(lr.content)
        except Exception as exc:
            print(f"  许可证下载失败 ({u}): {exc}")

    print(f"-> {CSS_OUT.relative_to(ROOT)}")
    print(f"-> {FONT_DIR.relative_to(ROOT)}/  ({total / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
