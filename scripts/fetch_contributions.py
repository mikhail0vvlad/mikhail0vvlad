#!/usr/bin/env python3
"""
fetch_contributions.py — реальный календарь вкладов без токена.

Ни GraphQL, ни personal access token не нужны: GitHub отдаёт тот же
фрагмент, что рисуется на странице профиля, публичным HTML по адресу
https://github.com/users/<username>/contributions

Забираем его requests, разбираем ячейки дней через BeautifulSoup и пишем
data/contributions.json: сырые дни плюс производная статистика.

Тот же фрагмент несёт заголовок с итогом за год — сверяем свою сумму с ним
и падаем при расхождении, чтобы смена разметки не утекла в репозиторий
пачкой нулей.

    python scripts/fetch_contributions.py [username]
"""
import json
import os
import re
import sys
from collections import OrderedDict
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

USER = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_USER", "mikhail0vvlad")
OUT = os.environ.get("OUT", "data/contributions.json")
URL = f"https://github.com/users/{USER}/contributions"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (profile-art; +https://github.com/%s)" % USER,
    "Accept": "text/html",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
}

COUNT_RE = re.compile(r"^\s*(No|\d[\d,]*)\s+contribution", re.I)
HEADER_RE = re.compile(r"^\s*(\d[\d,]*)\s+contributions?\s+in the last year", re.I)


def parse(soup):
    # текст подсказок несёт точное число вкладов за день
    tips = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        m = COUNT_RE.match(tip.get_text(" ", strip=True))
        if m:
            raw = m.group(1)
            tips[target] = 0 if raw.lower() == "no" else int(raw.replace(",", ""))

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        d = td.get("data-date")
        if not d:
            continue
        cid = td.get("id")
        count = tips.get(cid)
        if count is None:  # запасной путь для старой разметки
            raw = td.get("data-count")
            count = int(raw) if raw and raw.isdigit() else 0
        days.append({
            "date": d,
            "count": count,
            "level": int(td.get("data-level") or 0),
        })

    days.sort(key=lambda x: x["date"])
    return days


def header_total(soup):
    """Итог, который GitHub печатает над календарём, — независимая сверка."""
    h = soup.find(id="js-contribution-activity-description")
    if not h:
        return None
    m = HEADER_RE.match(h.get_text(" ", strip=True))
    return int(m.group(1).replace(",", "")) if m else None


def stats(days):
    today = date.today().isoformat()
    past = [d for d in days if d["date"] <= today]

    total = sum(d["count"] for d in past)

    # текущая серия: идём с конца; незавершённый сегодняшний день серию не рвёт
    cur = 0
    for i, d in enumerate(reversed(past)):
        if d["count"] > 0:
            cur += 1
        elif i == 0:
            continue
        else:
            break

    longest = run = 0
    for d in past:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    best = max(past, key=lambda d: d["count"]) if past else {"date": "", "count": 0}

    months = OrderedDict()
    for d in past:
        months[d["date"][:7]] = months.get(d["date"][:7], 0) + d["count"]

    active = sum(1 for d in past if d["count"] > 0)

    return {
        "total": total,
        "current_streak": cur,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "active_days": active,
        "days_tracked": len(past),
        "months": months,
    }


def main():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    days = parse(soup)
    if not days:
        raise SystemExit("не нашёл ни одной ячейки дня — разметка GitHub изменилась?")

    # Сверяем сумму по всему календарю (не по stats: там отброшены дни впереди
    # локальной даты, а часовой пояс профиля может быть впереди UTC).
    expected = header_total(soup)
    grand = sum(d["count"] for d in days)
    if expected is None:
        raise SystemExit("не нашёл заголовок с итогом за год — разметка GitHub изменилась?")
    if expected != grand:
        raise SystemExit(
            f"сумма по дням {grand} не сходится с итогом GitHub {expected} — "
            f"разметка GitHub изменилась?"
        )

    st = stats(days)

    payload = {
        "user": USER,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "stats": st,
        "days": days,
    }

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"{OUT}: {len(days)} дней, {st['total']} вкладов "
          f"(сходится с итогом GitHub: {expected}), "
          f"серия {st['current_streak']} (макс {st['longest_streak']})")


if __name__ == "__main__":
    main()
