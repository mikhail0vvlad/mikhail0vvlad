#!/usr/bin/env python3
"""
prep_photo.py — подготовка фотографии для ASCII-портрета.

Ровно освещённое лицо в ASCII превращается в неразличимое пятно.
Решают это четыре шага:

  1. rembg (u2net) вырезает фигуру из фона.
  2. CLAHE — адаптивное выравнивание гистограммы из OpenCV: именно оно
     вытаскивает светотень на плоском лице.
  3. Тональная кривая: смесь перцентильной растяжки и выравнивания
     гистограммы ВНУТРИ маски. Растяжка сохраняет естественное соотношение
     тонов, выравнивание разносит их по всей шкале — 35/65 даёт читаемое
     лицо без «кипящей» текстуры на одежде.
  4. Композит на ЧЁРНЫЙ. SVG рисуется светлым по тёмному, поэтому яркость
     пикселя = плотность глифа, а фон = пробел.

Запускается локально и только при смене фото:

    CROP=0.29,0.1875,0.625,0.4375 python scripts/prep_photo.py source-photo.png

Переменные окружения: CROP, TOP, PAD, MAX_SIDE, CLAHE_CLIP, CLAHE_GRID,
BLUR, EQ_MIX, GAMMA, FLOOR, P_LO, P_HI, REMBG_MODEL.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else "source-photo.png"
DST = sys.argv[2] if len(sys.argv) > 2 else "source-prepped.png"


def env_f(name, default):
    return float(os.environ.get(name, default))


CROP = os.environ.get("CROP")                 # "x0,y0,x1,y1" в долях 0..1
TOP = env_f("TOP", 1.0)                       # доля высоты фигуры после автокропа
PAD = env_f("PAD", 0.03)                      # отступ вокруг фигуры
MAX_SIDE = int(env_f("MAX_SIDE", 1400))       # даунскейл перед rembg
CLAHE_CLIP = env_f("CLAHE_CLIP", 3.0)
CLAHE_GRID = int(env_f("CLAHE_GRID", 8))
BLUR = env_f("BLUR", 0.9)                     # гасит текстуру ткани
EQ_MIX = env_f("EQ_MIX", 0.65)                # доля выравнивания гистограммы
GAMMA = env_f("GAMMA", 1.15)
FLOOR = env_f("FLOOR", 0.10)                  # минимальная плотность в силуэте
P_LO = env_f("P_LO", 2)
P_HI = env_f("P_HI", 98)


def main():
    img = Image.open(SRC).convert("RGB")

    if CROP:
        x0, y0, x1, y1 = (float(v) for v in CROP.split(","))
        w, h = img.size
        img = img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))

    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    # 1 — вырезаем фон. u2net весит ~176 МБ; дефолтная bria-rmbg — 1 ГБ и
    # укладывает CI по памяти. Модель качается один раз в ~/.rembg.
    from rembg import new_session, remove

    session = new_session(os.environ.get("REMBG_MODEL", "u2net"))
    arr = np.array(remove(img, session=session))          # RGBA
    alpha = arr[:, :, 3]

    # автокроп по маске
    ys, xs = np.where(alpha > 16)
    if len(xs):
        h, w = alpha.shape
        px, py = int(w * PAD), int(h * PAD)
        arr = arr[max(0, ys.min() - py):min(h, ys.max() + py),
                  max(0, xs.min() - px):min(w, xs.max() + px)]
        alpha = arr[:, :, 3]

    if TOP < 1.0:
        keep = max(1, int(arr.shape[0] * TOP))
        arr, alpha = arr[:keep], alpha[:keep]

    rgb = arr[:, :, :3]

    # 2 — CLAHE по каналу L
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=CLAHE_CLIP,
                        tileGridSize=(CLAHE_GRID, CLAHE_GRID)).apply(l)
    rgb = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    mask = alpha > 128

    # 3 — тональная кривая внутри маски
    src = cv2.GaussianBlur(gray, (0, 0), BLUR) if BLUR > 0 else gray

    lo, hi = np.percentile(gray[mask], (P_LO, P_HI)) if mask.any() else (0.0, 1.0)
    stretch = np.clip((src - lo) / max(hi - lo, 1e-3), 0.0, 1.0)

    if mask.any():
        cdf = np.histogram((gray[mask] * 255).astype(np.uint8),
                           256, (0, 256))[0].cumsum().astype(np.float32)
        cdf /= cdf[-1]
        equal = np.interp((src * 255).astype(np.uint8).ravel(),
                          np.arange(256), cdf).reshape(src.shape)
    else:
        equal = stretch

    tone = (1.0 - EQ_MIX) * stretch + EQ_MIX * equal
    tone = np.power(np.clip(tone, 0.0, 1.0), GAMMA)
    tone = FLOOR + tone * (1.0 - FLOOR)

    # 4 — композит на чёрный по альфе
    out = np.clip(tone * (alpha.astype(np.float32) / 255.0) * 255.0, 0, 255)
    out = np.where(mask | (alpha > 16), out, 0).astype(np.uint8)

    Image.fromarray(out, mode="L").save(DST)
    print(f"{SRC} -> {DST}  {out.shape[1]}x{out.shape[0]}")


if __name__ == "__main__":
    main()
