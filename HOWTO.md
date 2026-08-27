# Как это собрано

Профиль — это три анимированных SVG, которые README просто размещает.
Никаких сторонних сервисов статистики, токенов GitHub и JavaScript.

Ограничение, которое определяет всё: **GitHub вырезает `<script>` из README и
чистит почти весь инлайновый CSS, но SVG, встроенный через `<img>`,
отображает и проигрывает его SMIL/CSS-анимацию.** Поэтому вся анимация лежит
внутри самодостаточных SVG-файлов.

## Файлы

| файл | что это |
|---|---|
| `ascii-portrait.svg` | фото, превращённое в монохромный ASCII, печатается построчно |
| `info-card.svg` | панель в стиле neofetch, строки проявляются по очереди |
| `contrib-heatmap.svg` | реальный календарь 53×7, раскрывается диагональной волной |
| `data/contributions.json` | сырые дни + производная статистика |

## Ежедневное обновление

`.github/workflows/update-profile-art.yml` по cron дёргает
`fetch_contributions.py` и `render_heatmap_svg.py` и коммитит результат.

* `[skip ci]` в сообщении коммита не даёт воркфлоу перезапустить самого себя.
* `contents: write` разрешает боту пушить обратно.
* Первый прогон удобно запустить вручную во вкладке **Actions** →
  *update profile art* → *Run workflow*.

Токен не нужен: календарь берётся из публичного HTML
`https://github.com/users/<username>/contributions` — того же фрагмента,
что рисуется на странице профиля.

## Перегенерация вручную

Портрет и карточка статичны — пересобираются только при смене фото или текста.

```bash
python -m venv .venv && source .venv/bin/activate

# карточка и график (лёгкие зависимости)
pip install -r scripts/requirements.txt
python scripts/make_info_card.py
python scripts/fetch_contributions.py mikhail0vvlad
python scripts/render_heatmap_svg.py

# портрет (тяжёлые зависимости, нужны только при смене фото)
pip install -r scripts/requirements-portrait.txt
CROP=0.29,0.1875,0.625,0.4375 python scripts/prep_photo.py source-photo.png
python scripts/make_ascii_svg.py
```

Полезные ручки:

* `prep_photo.py` — `CROP` (кроп в долях кадра), `CLAHE_CLIP` (локальный
  контраст), `EQ_MIX` (баланс растяжки и выравнивания гистограммы),
  `FLOOR` (минимальная плотность внутри силуэта), `TOP`, `GAMMA`.
* `make_ascii_svg.py` — `COLS` (ширина сетки символов), `STATIC=1`
  (замороженный кадр для локального просмотра).
* `make_info_card.py` — контент лежит в списке `ROWS` прямо в скрипте.

## Ловушки GitHub Markdown

* Атрибут `style` вырезается. Единственный вертикальный отступ, который
  работает, — теги `<br>`.
* `<h1>` и `<h2>` рисуют линию во всю ширину. Если линия не нужна — `<h3>`.
* Ширины подогнаны: `392 + 468 = 860` — ровно ширина графика вкладов,
  поэтому края колонок совпадают.
* JavaScript и внешний CSS запрещены — анимация обязана жить внутри SVG.
