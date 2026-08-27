#!/usr/bin/env python3
"""
render_heatmap_svg.py — data/contributions.json -> анимированный SVG-календарь.

Классическая сетка 53 недели x 7 дней из закруглённых квадратов. Раскрывается
один раз по диагонали (волна слева-сверху направо-вниз) и замирает — никакого
зацикленного «свечения». Анимация — SMIL, поэтому GitHub проигрывает её из
README как обычную картинку.

    python scripts/render_heatmap_svg.py [data/contributions.json] [contrib-heatmap.svg]
"""
import json
import os
import sys
from datetime import date, datetime

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/contributions.json"
DST = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"
STATIC = os.environ.get("STATIC") == "1"

# нет -> ярче некуда (уровень 5 — неоновый максимум)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

BG = "#0d1117"
FRAME = "#21262d"
INK = "#c9d1d9"
DIM = "#7d8590"
KEY = "#39d353"

CELL = 12.0
GAP = 3.4
PITCH = CELL + GAP
RADIUS = 2.6

PADX = 22.0
TOP = 34.0          # полоска окна
LABEL_W = 30.0      # колонка «Mon/Wed/Fri»
MONTH_H = 20.0
FOOT_H = 62.0

WEEK_STEP = 0.030   # диагональная волна
DAY_STEP = 0.045
DUR = 0.34

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

FONT = ('font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'
        '&quot;DejaVu Sans Mono&quot;,monospace"')


def group_weeks(days):
    """Раскладываем плоский список по колонкам-неделям (колонка = вс..сб)."""
    weeks, cur = [], [None] * 7
    for d in days:
        wd = (datetime.strptime(d["date"], "%Y-%m-%d").weekday() + 1) % 7  # вс = 0
        if wd == 0 and any(c is not None for c in cur):
            weeks.append(cur)
            cur = [None] * 7
        cur[wd] = d
    if any(c is not None for c in cur):
        weeks.append(cur)
    return weeks


def fmt(n):
    return f"{n:,}".replace(",", " ")


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    days = data["days"]
    st = data["stats"]
    weeks = group_weeks(days)
    nw = len(weeks)

    grid_x = PADX + LABEL_W
    grid_y = TOP + MONTH_H
    W = grid_x + nw * PITCH - GAP + PADX
    H = grid_y + 7 * PITCH - GAP + FOOT_H

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
         f'aria-label="Календарь вкладов GitHub: {st["total"]} за год">']
    p.append(f'<rect width="{W:.0f}" height="{H:.0f}" rx="10" fill="{BG}"/>')
    p.append(f'<rect x="0.5" y="0.5" width="{W-1:.0f}" height="{H-1:.0f}" rx="10" '
             f'fill="none" stroke="{FRAME}"/>')
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        p.append(f'<circle cx="{PADX + i*15:.0f}" cy="17" r="4.5" fill="{c}" opacity="0.85"/>')

    # подписи месяцев — по первой неделе, в которой месяц сменился
    p.append(f'<g {FONT} font-size="11" fill="{DIM}">')
    seen = set()
    for wi, wk in enumerate(weeks):
        first = next((d for d in wk if d), None)
        if not first:
            continue
        m = int(first["date"][5:7])
        if m in seen:
            continue
        if wi and wi < nw - 2:
            seen.add(m)
            p.append(f'<text x="{grid_x + wi*PITCH:.1f}" y="{grid_y - 7:.1f}">'
                     f'{MONTHS[m-1]}</text>')
        elif wi == 0:
            seen.add(m)
    for row, label in DAY_LABELS.items():
        p.append(f'<text x="{PADX:.1f}" y="{grid_y + row*PITCH + CELL - 2.5:.1f}">'
                 f'{label}</text>')
    p.append("</g>")

    # сетка
    today = date.today().isoformat()
    p.append("<g>")
    for wi, wk in enumerate(weeks):
        for di, d in enumerate(wk):
            if d is None or d["date"] > today:
                continue
            lvl = d["level"]
            if lvl >= 4 and d["count"] >= max(1, st["best_day"]["count"] * 0.75):
                lvl = 5   # неоновый максимум для самых плотных дней
            x = grid_x + wi * PITCH
            y = grid_y + di * PITCH
            begin = wi * WEEK_STEP + di * DAY_STEP
            p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" '
                     f'rx="{RADIUS}" fill="{PALETTE[lvl]}"')
            if STATIC:
                p.append('/>')
            else:
                p.append(f' opacity="0">'
                         f'<animate attributeName="opacity" from="0" to="1" '
                         f'begin="{begin:.2f}s" dur="{DUR}s" fill="freeze"/>'
                         f'<animate attributeName="y" from="{y-7:.1f}" to="{y:.1f}" '
                         f'begin="{begin:.2f}s" dur="{DUR}s" fill="freeze" '
                         f'calcMode="spline" keySplines="0.2 0 0 1" keyTimes="0;1"/>'
                         f'</rect>')
    p.append("</g>")

    # подвал: слева статистика, справа легенда
    fy = grid_y + 7 * PITCH - GAP + 26
    p.append(f'<g {FONT} font-size="12.5">')
    p.append(f'<text x="{PADX:.1f}" y="{fy:.1f}" fill="{INK}">'
             f'<tspan fill="{KEY}">{fmt(st["total"])}</tspan> contributions in the last year'
             f'</text>')
    sub = (f'streak {st["current_streak"]}d · longest {st["longest_streak"]}d · '
           f'best {st["best_day"]["count"]} on {st["best_day"]["date"]} · '
           f'active {st["active_days"]}/{st["days_tracked"]}')
    p.append(f'<text x="{PADX:.1f}" y="{fy + 19:.1f}" font-size="11" fill="{DIM}">{sub}</text>')

    lx = W - PADX - (5 * 15 + 78)
    p.append(f'<text x="{lx:.1f}" y="{fy:.1f}" font-size="11" fill="{DIM}">Less</text>')
    for i in range(5):
        p.append(f'<rect x="{lx + 32 + i*15:.1f}" y="{fy - 10:.1f}" width="{CELL}" '
                 f'height="{CELL}" rx="{RADIUS}" fill="{PALETTE[i]}"/>')
    p.append(f'<text x="{lx + 32 + 5*15 + 4:.1f}" y="{fy:.1f}" font-size="11" '
             f'fill="{DIM}">More</text>')
    p.append("</g></svg>")

    with open(DST, "w", encoding="utf-8") as f:
        f.write("".join(p))
    print(f"{DST}  {nw} недель  {W:.0f}x{H:.0f}px  {os.path.getsize(DST)//1024} KB")


if __name__ == "__main__":
    main()
