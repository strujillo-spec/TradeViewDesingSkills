#!/usr/bin/env python3
"""Regenera los PNG @2x de assets/png/ a partir de los SVG de assets/svg/.

Úsalo cuando agregues o cambies un SVG (nuevo icono de estado, logo actualizado).
Usa cairosvg si está instalado; si no, playwright (Chromium).
    pip install cairosvg      # Linux / sandbox de Claude
    pip install playwright && python -m playwright install chromium   # macOS / Windows

    python scripts/build_assets.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "svg"
PNG = ROOT / "assets" / "png"

# Tamaño 1x (ancho, alto). El PNG se exporta al doble (@2x).
SIZES = {
    "tradeview-color": (170, 29),   # header
    "tradeview-white": (197, 31),   # footer
    "edge-white": (125, 38),        # footer
    "ui-copy": (20, 20),
    "ui-info": (16, 16),
    "ui-download": (16, 16),
    "brand-windows": (24, 24),
    "brand-web": (24, 24),
    "brand-macos": (85, 20),
    "brand-appstore": (28, 28),
    "brand-googleplay": (28, 28),
    "brand-apple": (15, 18),
    "brand-tradegatehub": (32, 40),
    "brand-up": (42, 32),
}
DEFAULT_ICON = (39, 39)             # icon-*.svg (Figma)
DEFAULT_SOCIAL = (48, 48)           # social-*.svg


def size_for(stem):
    if stem in SIZES:
        return SIZES[stem]
    if stem.startswith("social-"):
        return DEFAULT_SOCIAL
    return DEFAULT_ICON


def render_cairo(jobs):
    import cairosvg
    for svg, out, w, h in jobs:
        cairosvg.svg2png(url=str(svg), write_to=str(out), output_width=w * 2, output_height=h * 2)


def render_playwright(jobs):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(device_scale_factor=2)
        for svg, out, w, h in jobs:
            src = re.sub(r"<\?xml[^>]*>", "", svg.read_text())
            src = re.sub(r'^(<svg[^>]*?)\s(?:width|height)="[^"]*"', r"\1", src.strip())
            src = re.sub(r'^(<svg[^>]*?)\s(?:width|height)="[^"]*"', r"\1", src)
            src = src.replace("<svg", f'<svg width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet"', 1)
            pg.set_viewport_size({"width": w, "height": h})
            pg.set_content(f'<html><body style="margin:0;background:transparent">{src}</body></html>')
            pg.screenshot(path=str(out), omit_background=True, clip={"x": 0, "y": 0, "width": w, "height": h})
        br.close()


def main():
    PNG.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    jobs = []
    for svg in sorted(SVG.glob("*.svg")):
        if only and svg.stem not in only:
            continue
        w, h = size_for(svg.stem)
        jobs.append((svg, PNG / f"{svg.stem}@2x.png", w, h))
    try:
        render_cairo(jobs)
    except (ImportError, OSError):
        try:
            render_playwright(jobs)
        except ImportError:
            sys.exit("Falta un renderizador. Instala cairosvg o playwright (ver docstring).")
    for _, out, w, h in jobs:
        print(f"{out.name}  ({w*2}x{h*2})")


if __name__ == "__main__":
    main()
