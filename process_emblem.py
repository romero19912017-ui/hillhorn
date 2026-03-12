# -*- coding: utf-8 -*-
"""Process emblem: blue-orange fill inside, transparent background, add Hillhorn text."""

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
JPG = ROOT / "эмблема.jpg"
OUT = ROOT / "emblem.png"

# Dark blue #1a3a5c, orange #e87d3a
BLUE = (26, 58, 92)
ORANGE = (232, 125, 58)

def main():
    if not JPG.exists():
        print(f"Not found: {JPG}")
        return
    img = Image.open(JPG).convert("L")
    gray = np.array(img, dtype=float)
    h, w = gray.shape
    # Figure = dark pixels, background = light
    bg_thresh = 240
    figure = gray < bg_thresh
    t = np.clip(gray / 255.0, 0, 1)
    # Inverted: dark -> orange, light -> blue
    nr = (1 - t) * ORANGE[0] + t * BLUE[0]
    ng = (1 - t) * ORANGE[1] + t * BLUE[1]
    nb = (1 - t) * ORANGE[2] + t * BLUE[2]
    result = np.zeros((h, w, 4), dtype=np.uint8)
    result[:, :, 0] = nr.astype(np.uint8)
    result[:, :, 1] = ng.astype(np.uint8)
    result[:, :, 2] = nb.astype(np.uint8)
    result[:, :, 3] = np.where(figure, 255, 0).astype(np.uint8)
    # Blue contour on edges
    edges = img.filter(ImageFilter.FIND_EDGES)
    arr_e = np.array(edges)
    contour = (arr_e > 20) & figure
    result[contour, 0] = BLUE[0]
    result[contour, 1] = BLUE[1]
    result[contour, 2] = BLUE[2]
    result[contour, 3] = 255
    out_img = Image.fromarray(result)
    # Add padding at bottom for text
    w, h = out_img.size
    pad = 48
    canvas = Image.new("RGBA", (w, h + pad), (255, 255, 255, 0))
    canvas.paste(out_img, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    text = "Hillhorn"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (w - tw) // 2
    draw.text((x, h + 8), text, fill=BLUE, font=font)
    canvas.save(OUT)
    print(f"Saved: {OUT}")

if __name__ == "__main__":
    main()
