#!/usr/bin/env python3
"""
make_ascii_svg.py - превращает подготовленное фото в самопечатающийся ASCII-SVG.

Ключевые решения:
  * Монохром. Один цвет заливки. Радужная раскраска по символам -- ровно то,
    из-за чего большинство ASCII-портретов выглядят дёшево.
  * Высокий контраст. Белый фон уходит в глиф пробела, поэтому "печатается"
    только фигура.
  * Анимация -- чистый SMIL внутри SVG: GitHub вырезает <script> и почти весь
    инлайновый CSS из README, но SVG, встроенный через <img>, проигрывает
    SMIL как есть.
  * textLength + lengthAdjust="spacingAndGlyphs" жёстко фиксирует ширину
    строки, поэтому сетка не разъезжается на любом моноширинном шрифте.

    python scripts/make_ascii_svg.py [source-prepped.png] [avi-ascii.svg]
"""
import os
import sys
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
DST = sys.argv[2] if len(sys.argv) > 2 else "ascii-portrait.svg"

# " " в начале очищает фон в ноль.
# Картинка приходит светлым-по-чёрному, SVG тоже светлый по тёмному:
# яркость пикселя -> плотность глифа, чёрный фон -> пробел.
RAMP = " .`:-=+*cs#%@"

COLS = int(os.environ.get("COLS", 84))
CW = 7.0          # ширина знакоместа
CH = 11.6         # высота строки
FONT = 11.0
PAD = 18.0

BG = "#0d1117"
FRAME = "#21262d"
INK = "#c9d1d9"
CURSOR = "#39d353"

ROW_DUR = 0.42    # сколько печатается одна строка
STAGGER = 0.048   # сдвиг между строками
STATIC = os.environ.get("STATIC") == "1"

ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def esc(s):
    return "".join(ESC.get(c, c) for c in s)


def to_rows(path):
    im = Image.open(path).convert("L")
    w, h = im.size
    rows = max(1, round(COLS * (h / w) * (CW / CH)))
    im = im.resize((COLS, rows), Image.LANCZOS)
    px = im.load()
    n = len(RAMP) - 1
    out = []
    for y in range(rows):
        line = []
        for x in range(COLS):
            v = px[x, y] / 255.0          # 0 фон .. 1 самый яркий
            line.append(RAMP[round(v * n)])
        out.append("".join(line).rstrip())
    return out


def main():
    rows = to_rows(SRC)
    text_w = COLS * CW
    W = text_w + PAD * 2
    H = len(rows) * CH + PAD * 2 + 16

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
        f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="ASCII-портрет">'
    )
    p.append(f'<rect width="{W:.0f}" height="{H:.0f}" rx="10" fill="{BG}"/>')
    p.append(
        f'<rect x="0.5" y="0.5" width="{W-1:.0f}" height="{H-1:.0f}" rx="10" '
        f'fill="none" stroke="{FRAME}"/>'
    )
    # титульная полоска в духе терминала
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        p.append(f'<circle cx="{PAD + i*13:.0f}" cy="15" r="4" fill="{c}" opacity="0.85"/>')

    # клипы для построчной печати
    p.append("<defs>")
    for i in range(len(rows)):
        if not rows[i]:
            continue
        y = PAD + 16 + i * CH - CH + 2.5
        p.append(f'<clipPath id="r{i}"><rect x="{PAD:.1f}" y="{y:.1f}" height="{CH:.1f}" ')
        if STATIC:
            p.append(f'width="{text_w:.1f}"/>')
        else:
            begin = i * STAGGER
            p.append(
                f'width="0">'
                f'<animate attributeName="width" from="0" to="{text_w:.1f}" '
                f'begin="{begin:.2f}s" dur="{ROW_DUR}s" fill="freeze" '
                f'calcMode="linear"/></rect>'
            )
        p.append("</clipPath>")
    p.append("</defs>")

    p.append(
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'
        f'&quot;DejaVu Sans Mono&quot;,monospace" font-size="{FONT}" fill="{INK}">'
    )
    for i, line in enumerate(rows):
        if not line:
            continue
        y = PAD + 16 + i * CH
        p.append(
            f'<text x="{PAD:.1f}" y="{y:.1f}" xml:space="preserve" '
            f'textLength="{text_w:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'clip-path="url(#r{i})">{esc(line.ljust(COLS))}</text>'
        )
    p.append("</g>")

    # каретка, бегущая по краю печати
    if not STATIC:
        for i, line in enumerate(rows):
            if not line:
                continue
            begin = i * STAGGER
            y = PAD + 16 + i * CH - CH + 2.5
            p.append(
                f'<rect x="{PAD:.1f}" y="{y:.1f}" width="{CW:.1f}" height="{CH:.1f}" '
                f'fill="{CURSOR}" opacity="0">'
                f'<set attributeName="opacity" to="0.75" begin="{begin:.2f}s"/>'
                f'<set attributeName="opacity" to="0" begin="{begin + ROW_DUR:.2f}s"/>'
                f'<animate attributeName="x" from="{PAD:.1f}" to="{PAD + text_w:.1f}" '
                f'begin="{begin:.2f}s" dur="{ROW_DUR}s" fill="freeze"/></rect>'
            )

    p.append("</svg>")

    with open(DST, "w", encoding="utf-8") as f:
        f.write("".join(p))
    print(f"{DST}  {COLS}x{len(rows)}  {W:.0f}x{H:.0f}px  {os.path.getsize(DST)//1024} KB")


if __name__ == "__main__":
    main()
