#!/usr/bin/env python3
"""Regenera los PNG @2x de assets/png/ a partir de los SVG de assets/svg/.

Úsalo cuando agregues o cambies un SVG (nuevo icono de estado, logo actualizado).
Requiere cairosvg:  pip install cairosvg --break-system-packages

    python scripts/build_assets.py
"""
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    sys.exit("Falta cairosvg. Instala con: pip install cairosvg --break-system-packages")

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "svg"
PNG = ROOT / "assets" / "png"

# Tamaño 1x (ancho, alto). El PNG se exporta al doble (@2x).
SIZES = {
    "tradeview-color": (170, 29),   # header
    "tradeview-white": (197, 31),   # footer
    "edge-white": (125, 38),        # footer
}
DEFAULT_ICON = (36, 36)             # icon-*.svg
DEFAULT_SOCIAL = (48, 48)           # social-*.svg


def size_for(stem):
    if stem in SIZES:
        return SIZES[stem]
    if stem.startswith("social-"):
        return DEFAULT_SOCIAL
    return DEFAULT_ICON


def main():
    PNG.mkdir(parents=True, exist_ok=True)
    for svg in sorted(SVG.glob("*.svg")):
        w, h = size_for(svg.stem)
        out = PNG / f"{svg.stem}@2x.png"
        cairosvg.svg2png(url=str(svg), write_to=str(out), output_width=w * 2, output_height=h * 2)
        print(f"{out.name}  ({w*2}x{h*2})")


if __name__ == "__main__":
    main()
