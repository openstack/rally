# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Build the "Who uses Rally" logo grid from sources.yaml.

Every logo is embedded into one SVG, so the page needs a single image and
the grid looks the same on every docs theme. Logos are scaled to the same
visual area, so wide wordmarks and square badges look equally heavy.
"""

from __future__ import annotations

import base64
import html
import math
import pathlib
import re
import struct

import yaml

import rally


ROOT = pathlib.Path(rally.__file__).resolve().parents[1]
LOGOS = ROOT / "doc" / "logos"
OUTPUT = ROOT / "doc" / "source" / "images" / "who_uses_rally.svg"

COLS = 6
CELL_W = 180
CELL_H = 100
PAD = 18
AREA = 5200
MAX_W = CELL_W - 2 * PAD
MAX_H = CELL_H - 2 * PAD

_VIEWBOX = re.compile(
    r'viewBox="\s*[-\d.e]+[ ,]+[-\d.e]+[ ,]+([\d.e]+)[ ,]+([\d.e]+)'
)


def aspect(fname: str, data: bytes) -> float:
    if fname.endswith(".png"):
        width, height = struct.unpack(">II", data[16:24])
        return width / height
    head = re.search(r"<svg[^>]*>", data.decode(), re.S)
    if head is None:
        raise ValueError(f"{fname}: no <svg> element")
    vb = _VIEWBOX.search(head.group(0))
    if vb is not None:
        return float(vb.group(1)) / float(vb.group(2))
    width = re.search(r'\swidth="([\d.]+)', head.group(0))
    height = re.search(r'\sheight="([\d.]+)', head.group(0))
    if width is None or height is None:
        raise ValueError(f"{fname}: no viewBox and no width/height")
    return float(width.group(1)) / float(height.group(1))


def normalize(data: bytes) -> bytes:
    """Give the root <svg> unitless width/height taken from its viewBox.

    Physical units (mm, pt) are fine for browsers but some renderers reject
    them inside an embedded image.
    """
    text = data.decode()
    head = re.search(r"<svg[^>]*>", text, re.S)
    if head is None:
        return data
    vb = _VIEWBOX.search(head.group(0))
    if vb is None:
        return data
    tag = re.sub(r'\s(width|height)="[^"]*"', "", head.group(0))
    tag = tag.replace(
        "<svg", f'<svg width="{vb.group(1)}" height="{vb.group(2)}"', 1
    )
    return (text[: head.start()] + tag + text[head.end():]).encode()


def build(logos: list[dict[str, str]]) -> str:
    rows = math.ceil(len(logos) / COLS)
    width, height = COLS * CELL_W, rows * CELL_H
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="Organizations that use Rally">',
        f'<rect width="{width}" height="{height}" rx="12" fill="#ffffff"/>',
    ]
    for i, logo in enumerate(logos):
        data = (LOGOS / logo["file"]).read_bytes()
        ratio = aspect(logo["file"], data)
        h = math.sqrt(AREA / ratio)
        w = h * ratio
        scale = min(1.0, MAX_W / w, MAX_H / h)
        w, h = w * scale, h * scale
        x = i % COLS * CELL_W + (CELL_W - w) / 2
        y = i // COLS * CELL_H + (CELL_H - h) / 2
        if logo["file"].endswith(".png"):
            mime = "image/png"
        else:
            mime = "image/svg+xml"
            data = normalize(data)
        b64 = base64.b64encode(data).decode()
        parts.append(
            f'<image x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" '
            f'height="{h:.1f}" href="data:{mime};base64,{b64}">'
            f"<title>{html.escape(logo['name'])}</title></image>"
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    logos = yaml.safe_load((LOGOS / "sources.yaml").read_text())
    OUTPUT.write_text(build(logos))
    print(f"{len(logos)} logos written to {OUTPUT}")


if __name__ == "__main__":
    main()
