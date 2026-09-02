#!/usr/bin/env python3
"""
make_info_card.py — SVG-панель в стиле neofetch, собирается руками.

Контент держим здесь, а не в графике вкладов: график и так показывает
статистику GitHub, поэтому карточка отвечает за то, чего цифры не расскажут.

Строки проявляются по очереди с лёгким сдвигом — панель выглядит так, будто
печатается рядом с портретом. Анимация — чистый SMIL: GitHub вырезает
<script> и почти весь инлайновый CSS из README, но SVG через <img> играет.

    python scripts/make_info_card.py            # info-card.svg
    STATIC=1 python scripts/make_info_card.py   # замороженный кадр для превью
"""
import os

DST = os.environ.get("DST", "info-card.svg")
STATIC = os.environ.get("STATIC") == "1"

BG = "#0d1117"
FRAME = "#21262d"
INK = "#c9d1d9"
DIM = "#7d8590"
KEY = "#39d353"      # ключи — зелёный
ACCENT = "#58a6ff"   # заголовок — синий
MAGENTA = "#bc8cff"

USER = "mikhail0vvlad"
HOST = "moscow"

# (ключ, значение, цвет значения) | None — пустая строка | "---" — разделитель
ROWS = [
    ("Role",         "Android Developer",                                 INK),
    ("Education",    "RTU MIREA — Software Engineering",                  INK),
    None,
    ("Core",         "Kotlin · Jetpack Compose · Coroutines / Flow",      INK),
    ("Android",      "Navigation · Room · DataStore · WorkManager",       INK),
    ("Network",      "Retrofit · OkHttp · REST",                          INK),
    ("Architecture", "MVVM / MVI · Multi-module · DI",                    INK),
    ("Engineering",  "Gradle · CI/CD · Unit & UI Testing",                INK),
    None,
    ("Experience",   "product features end-to-end",                      INK),
    ("",             "team development · code review · API integration", INK),
    None,
    ("Building",     "Android apps with product-focused UX",              ACCENT),
    ("Pinned",       "powerlifting-assistant — Android + Ktor backend",   MAGENTA),
    None,
    ("Also",         "Python · Java · C++",                               DIM),
    ("Contact",      "t.me/mikhail0vvlad · vk.com/mikhail0vvlad",         ACCENT),
]

PALETTE_DIM = ["#484f58", "#f85149", "#3fb950", "#d29922",
               "#58a6ff", "#bc8cff", "#39c5cf", "#b1bac4"]
PALETTE_HI = ["#6e7681", "#ff7b72", "#56d364", "#e3b341",
              "#79c0ff", "#d2a8ff", "#56d4dd", "#f0f6fc"]

FONT = 15.0
CW = 9.02          # ширина знакоместа при textLength
LH = 26.0          # межстрочный интервал
PADX = 26.0
PADY = 44.0        # место под полоску окна
KEYW = 12          # ширина колонки ключей

STEP = 0.09        # задержка между строками
DUR = 0.34
LEAD = 0.25        # анимация стартует чуть позже портрета

ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}


def esc(s):
    return "".join(ESC.get(c, c) for c in s)


def main():
    lines = []   # (raw_text, [(text, fill)])
    lines.append(("mikhail0vvlad@github ~ $ neofetch",
                  [("mikhail0vvlad", KEY), ("@github", ACCENT),
                   (" ~ $ ", DIM), ("neofetch", INK)]))
    lines.append(("", []))

    title = f"{USER}@{HOST}"
    lines.append((title, [(USER, KEY), ("@", DIM), (HOST, ACCENT)]))
    lines.append(("-" * len(title), [("-" * len(title), DIM)]))

    for row in ROWS:
        if row is None:
            lines.append(("", []))
            continue
        k, v, color = row
        key = k.ljust(KEYW)
        sep = ": " if k else "  "
        lines.append((key + sep + v,
                      [(key, KEY), (sep, DIM), (v, color)]))

    lines.append(("", []))
    lines.append(("__PALETTE__", []))
    lines.append(("__PALETTE__", []))

    widest = max(len(t) for t, _ in lines if t != "__PALETTE__")
    W = widest * CW + PADX * 2
    H = PADY + len(lines) * LH + PADY * 0.55

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="neofetch: {USER}">']
    p.append(f'<rect width="{W:.0f}" height="{H:.0f}" rx="10" fill="{BG}"/>')
    p.append(f'<rect x="0.5" y="0.5" width="{W-1:.0f}" height="{H-1:.0f}" rx="10" '
             f'fill="none" stroke="{FRAME}"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        p.append(f'<circle cx="{PADX + i*16:.0f}" cy="18" r="5" fill="{c}" opacity="0.85"/>')

    p.append(f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'
             f'&quot;DejaVu Sans Mono&quot;,monospace" font-size="{FONT}">')

    pal_i = 0
    for i, (raw, spans) in enumerate(lines):
        y = PADY + i * LH
        begin = LEAD + i * STEP
        p.append("<g")
        if not STATIC:
            p.append(' opacity="0"')
        p.append(">")
        if not STATIC:
            p.append(f'<animate attributeName="opacity" from="0" to="1" '
                     f'begin="{begin:.2f}s" dur="{DUR}s" fill="freeze"/>')
            p.append(f'<animateTransform attributeName="transform" type="translate" '
                     f'from="-10 0" to="0 0" begin="{begin:.2f}s" dur="{DUR}s" '
                     f'fill="freeze" calcMode="spline" keySplines="0.2 0 0 1" '
                     f'keyTimes="0;1"/>')

        if raw == "__PALETTE__":
            colors = PALETTE_DIM if pal_i == 0 else PALETTE_HI
            pal_i += 1
            for j, c in enumerate(colors):
                p.append(f'<rect x="{PADX + j*26:.1f}" y="{y-14:.1f}" width="22" '
                         f'height="16" rx="3" fill="{c}"/>')
        elif raw:
            p.append(f'<text x="{PADX:.1f}" y="{y:.1f}" xml:space="preserve" '
                     f'textLength="{len(raw)*CW:.1f}" lengthAdjust="spacingAndGlyphs">')
            for txt, fill in spans:
                p.append(f'<tspan fill="{fill}">{esc(txt)}</tspan>')
            p.append("</text>")
        p.append("</g>")

    # мигающая каретка в конце
    y = PADY + (len(lines) - 1) * LH + LH
    p.append(f'<rect x="{PADX:.1f}" y="{y-14:.1f}" width="{CW:.1f}" height="16" '
             f'fill="{KEY}" opacity="0">')
    if not STATIC:
        end = LEAD + len(lines) * STEP
        p.append(f'<animate attributeName="opacity" values="0;0.9;0.9;0" dur="1.1s" '
                 f'begin="{end:.2f}s" repeatCount="indefinite"/>')
    p.append("</rect>")
    p.append("</g></svg>")

    with open(DST, "w", encoding="utf-8") as f:
        f.write("".join(p))
    print(f"{DST}  {W:.0f}x{H:.0f}px  {os.path.getsize(DST)//1024} KB")


if __name__ == "__main__":
    main()
