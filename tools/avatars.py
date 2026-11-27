"""把 CrossPet 的头像（人物贴在画布左下角）重新居中。

  python tools/avatars.py      sources/crosspet/*.webp -> avatars/*.webp

人物按不透明部分的范围裁出来，放进正方形画布：水平居中（可按 SHIFT 微调），
底边对齐画布底边（胸像下沿本来就会被圆裁掉），上方留 TOP 的空，再缩放到 SIZE。
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources" / "crosspet"
OUT = ROOT / "avatars"
SIZE = 192
TOP = 0.06  # 头顶上方留的空，占画布边长的比例
SHIFT = {"doubao": 0.08}  # 某张脸不在人物范围正中时，按画布边长的比例左右挪，正数往右


def recenter(src: Path, shift: float = 0.0) -> Image.Image:
    im = Image.open(src).convert("RGBA")
    bbox = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    fig = im.crop(bbox)
    w, h = fig.size
    side = max(w, round(h / (1 - TOP)))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(fig, (round((side - w) / 2 + shift * side), side - h))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


if __name__ == "__main__":
    for src in sorted(SRC.glob("*.webp")):
        out = OUT / src.name
        recenter(src, SHIFT.get(src.stem, 0.0)).save(out, "WEBP", quality=90, method=6)
        print(out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")
