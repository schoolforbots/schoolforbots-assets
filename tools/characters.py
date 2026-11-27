"""生成 other、老师、陪练三个形象：拿 CrossPet 的头像当画风参考，用本机 ComfyUI 在白底上画新角色，
再抠成透明底、按 tools/avatars.py 的办法裁切居中。

  python tools/characters.py render [角色...] [--seeds=1,2,3]   -> sources/raw/char-<角色>-<种子>.png（白底原图）
                                                                   和 sources/raw/char-<角色>-<种子>.webp（透明、居中）
  python tools/characters.py adopt 角色 种子                       -> 选定一张：复制成 sources/characters/<角色>.png 和 avatars/<角色>.webp

参考图用的是 CrossPet 的形象，所以生成的形象也按 CC BY-NC-SA 4.0 授权（见 avatars/LICENSE.md）。
"""
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import avatars  # noqa: E402
import scenes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "sources" / "raw"
REF = ROOT / "sources" / "crosspet" / "kimi.webp"  # 画风参考：胸像、探头的构图
SIZE = 1024

STYLE = (
    "参考这张图的画风画一个全新的角色：同样的 Q 版二次元头像风格、同样的线条和上色方式、同样的构图（大头的胸像，人物从画面下边探出来，双手扶在画面下边缘），"
    "但不要画图里这个角色本身，换成下面描述的新角色。纯白色背景，没有文字，没有其它人物。"
)
CHARACTERS = {
    "other": (
        "新角色是一个普通的学生少女：灰白色的及肩短发，头发上别着一个浅蓝色的问号形状的发卡，"
        "穿着白衬衫和深灰色西装外套的学校制服，系着浅蓝色领结，表情好奇，歪着头，眼睛是浅灰蓝色。"
    ),
    "teacher": (
        "新角色是一位温柔的年轻女老师：深棕色的长发在脑后挽成低马尾，戴着一副细细的金色圆框眼镜，"
        "穿着米白色的衬衫和浅驼色的西装外套，一只手里拿着一本教科书和一支粉笔，温柔地微笑，眼睛是琥珀色。"
    ),
    "sparring": (
        "新角色是一个牌桌上的荷官少女：酒红色的短发，额头上戴着一顶绿色半透明的荷官遮阳帽，"
        "穿着白衬衫、黑色马甲和红色领结，双手捏着一把扇形摊开的扑克牌，露出自信又调皮的笑容，眼睛是金色。"
    ),
}


def reference():
    """把参考头像放大、垫上白底，放进 ComfyUI 的 input。"""
    im = Image.open(REF).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
    bg = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    bg.alpha_composite(im)
    name = "sfb_char_ref.png"
    bg.convert("RGB").save(scenes.COMFY_INPUT / name)
    return name


def cutout(img, thresh=235):
    """白底 -> 透明：从画面边缘往里灌，只去掉和边缘连着的近白色，人物身上的白色（衬衫、高光）保留。"""
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    h, w, _ = rgb.shape
    white = (rgb.min(axis=2) >= thresh) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 20)
    bg = np.zeros((h, w), bool)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not bg[y, x]:
                bg[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and white[yy, xx] and not bg[yy, xx]:
                bg[yy, xx] = True
                q.append((yy, xx))
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    out = img.convert("RGBA")
    a = Image.fromarray(alpha).filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(0.8))
    out.putalpha(a)
    return out


def render(names, seeds):
    ref = reference()
    RAW.mkdir(parents=True, exist_ok=True)
    for name in names:
        for seed in seeds:
            graph = scenes.workflow(ref, STYLE + CHARACTERS[name], seed)
            graph["11"]["inputs"].update({"width": SIZE, "height": SIZE})
            raw = RAW / f"char-{name}-{seed}.png"
            raw.write_bytes(scenes.comfy(ref, "", seed, graph))
            cut = RAW / f"char-{name}-{seed}-cut.png"
            cutout(Image.open(raw)).save(cut)
            out = RAW / f"char-{name}-{seed}.webp"
            avatars.recenter(cut).save(out, "WEBP", quality=90, method=6)
            print(out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB", flush=True)


def adopt(name, seed):
    src = ROOT / "sources" / "characters"
    src.mkdir(parents=True, exist_ok=True)
    (src / f"{name}.png").write_bytes((RAW / f"char-{name}-{seed}.png").read_bytes())
    out = ROOT / "avatars" / f"{name}.webp"
    out.write_bytes((RAW / f"char-{name}-{seed}.webp").read_bytes())
    print(out.relative_to(ROOT))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
    if args[0] == "render":
        render(args[1:] or list(CHARACTERS), [int(x) for x in opts.get("seeds", "1,2,3").split(",")])
    elif args[0] == "adopt":
        adopt(args[1], int(args[2]))
