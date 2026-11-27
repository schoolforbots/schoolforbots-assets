"""校园布局：在俯视平面上定义每栋楼和每块场地，投影成等距视角（斜 45°）。

  python tools/campus_layout.py diagram   白模示意图（带名字和放头像的区域）-> sources/layouts/campus-diagram.png
  python tools/campus_layout.py coords    打印每个地点在成图上的坐标（0–1 比例）

平面坐标 (u, v) 是校园所在的正方形，0–L。u 往屏幕右下走，v 往屏幕左下走，
(0, 0) 在屏幕最上方。为了让画面铺满 16:10，菱形比画面大，左右两角和上下边会被裁掉，
裁掉的部分是校外的马路和树，只做点缀。
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "layouts"

W, H = 1664, 1040
A = 1150  # 平面边长 1 投影后的半宽（像素）
L = 1.40  # 校园在平面上的边长。菱形比画面大一些，只在四个角露出校外
CX, Y0 = W / 2, H / 2 - L * A / 2  # 校园中心对准画面中心
OFF = L - (H / 2 + 40) / (A / 2)  # 让 at() 的 Y 和原来一样：Y=0 在画面上方 40 像素处
FLOOR = 8  # 一层楼在屏幕上的高度（像素）

FONT = "C:/Windows/Fonts/msyh.ttc"


def iso(u, v, z=0.0):
    """平面坐标 + 高度（像素） -> 屏幕坐标。"""
    return (CX + (u - v) * A, Y0 + (u + v) * A / 2 - z)


def at(X, Y):
    """按"屏幕上的大致位置"给平面坐标：X = u - v（左右），Y = u + v（上下）。"""
    return ((Y + OFF + X) / 2, (Y + OFF - X) / 2)


def rect(u, v, du, dv):
    return [(u, v), (u + du, v), (u + du, v + dv), (u, v + dv)]


def rects_union_outline(parts):
    """几个矩形拼成的形状（L、丁、工）：分别画，不求外轮廓。"""
    return parts


def ellipse(u, v, ru, rv, n=40):
    return [(u + ru * math.cos(t), v + rv * math.sin(t)) for t in (2 * math.pi * i / n for i in range(n))]


def stadium(u, v, length, width, n=16):
    """跑道形：沿 u 方向的长条，两头是半圆。"""
    r = width / 2
    pts = []
    for i in range(n + 1):
        t = -math.pi / 2 + math.pi * i / n
        pts.append((u + length / 2 - r + r * math.cos(t), v + r * math.sin(t)))
    for i in range(n + 1):
        t = math.pi / 2 + math.pi * i / n
        pts.append((u - length / 2 + r + r * math.cos(t), v + r * math.sin(t)))
    return pts


# ---------------------------------------------------------------- 布局

def layout():
    """每一项：名字、若干个（平面多边形, 楼层数[, 离地几层]）、地面场地、放头像的区域（平面矩形）、是否预留。"""
    items = {}

    # 高中部：工字型，5 层。两条长楼沿 v 方向，中间一条短楼连起来，院子开口朝屏幕下方。
    u, v = at(-0.34, 0.50)
    items["senior"] = {
        "label": "高中部",
        "blocks": [(rect(u - 0.135, v - 0.09, 0.035, 0.28), 5), (rect(u + 0.10, v - 0.09, 0.035, 0.28), 5), (rect(u - 0.10, v - 0.015, 0.20, 0.03), 5)],
        "areas": [rect(u - 0.06, v + 0.03, 0.12, 0.12)],
    }

    # 初中部：丁字型，4 层。一条横楼在后，竖楼从中间伸向屏幕下方，两侧是院子。
    u, v = at(0.06, 0.43)
    items["junior"] = {
        "label": "初中部",
        "blocks": [(rect(u - 0.13, v - 0.10, 0.26, 0.035), 4), (rect(u - 0.0175, v - 0.065, 0.035, 0.14), 4)],
        "areas": [rect(u - 0.12, v - 0.04, 0.065, 0.09), rect(u + 0.045, v - 0.04, 0.065, 0.09)],
    }

    # 小学部：L 型，2 层，院子在 L 的内角，朝屏幕下方。
    u, v = at(-0.52, 0.95)
    items["primary"] = {
        "label": "小学部",
        "blocks": [(rect(u - 0.09, v - 0.09, 0.18, 0.035), 2), (rect(u - 0.09, v - 0.055, 0.035, 0.145), 2)],
        "areas": [rect(u - 0.045, v - 0.045, 0.12, 0.12)],
    }

    # 社团活动中心：参考新加坡国家图书馆，两栋楼 + 高处的空中连廊，中间是中庭。
    u, v = at(0.36, 0.86)
    items["club"] = {
        "label": "社团活动中心",
        "blocks": [(rect(u - 0.09, v - 0.06, 0.05, 0.13), 9), (rect(u + 0.04, v - 0.06, 0.05, 0.13), 7), (rect(u - 0.04, v - 0.01, 0.08, 0.02), 1, 5)],
        "areas": [rect(u - 0.09, v + 0.06, 0.12, 0.12)],
    }

    # 中心广场：闲逛的人。
    u, v = at(-0.06, 0.88)
    items["plaza"] = {
        "label": "中心广场",
        "blocks": [],
        "ground": [ellipse(u, v, 0.10, 0.10)],
        "areas": [rect(u - 0.07, v - 0.07, 0.14, 0.14)],
    }

    # 操场：高校 400 米跑道 + 足球场 + 一侧看台。预留。
    u, v = at(0.42, 0.42)
    items["playground"] = {
        "label": "操场（预留）",
        "blocks": [(rect(u - 0.10, v - 0.115, 0.20, 0.02), 2)],
        "ground": [stadium(u, v, 0.26, 0.15)],
        "areas": [rect(u - 0.06, v - 0.04, 0.12, 0.08)],
        "reserved": True,
    }

    # 篮球场：挨着操场。预留。
    u, v = at(0.58, 0.70)
    items["basketball"] = {
        "label": "篮球场（预留）",
        "blocks": [],
        "ground": [rect(u - 0.045, v - 0.06, 0.09, 0.12)],
        "areas": [rect(u - 0.035, v - 0.05, 0.07, 0.10)],
        "reserved": True,
    }

    # 图书馆：参考 The Star Vista，有机曲线 + 中间的露天阶梯剧场。预留。
    u, v = at(-0.40, 1.48)
    items["library"] = {
        "label": "图书馆（预留）",
        "blocks": [(ellipse(u, v, 0.09, 0.075), 4)],
        "areas": [rect(u - 0.035, v - 0.03, 0.07, 0.06)],
        "areaOnRoof": True,  # 头像放在楼中间的露天阶梯剧场里，不检查遮挡
        "reserved": True,
    }

    # 剧院：参考 Esplanade，两个"榴莲"圆壳，在河边。预留。
    u, v = at(0.36, 1.50)
    items["theatre"] = {
        "label": "剧院（预留）",
        "blocks": [(ellipse(u - 0.05, v, 0.05, 0.05), 4), (ellipse(u + 0.05, v - 0.01, 0.04, 0.04), 3)],
        "areas": [rect(u - 0.05, v + 0.06, 0.11, 0.035)],
        "reserved": True,
    }

    # 校门 + 公告栏：不放人。
    u, v = at(0.0, 1.78)
    items["gate"] = {
        "label": "校门 · 公告栏",
        "blocks": [(rect(u - 0.05, v - 0.01, 0.02, 0.02), 4), (rect(u + 0.03, v - 0.01, 0.02, 0.02), 4), (rect(u - 0.05, v - 0.01, 0.10, 0.02), 1, 4)],
        "areas": [],
    }

    # 小卖部：一层小店，带遮阳棚，在主路旁。预留。
    u, v = at(0.14, 1.52)
    items["shop"] = {
        "label": "小卖部（预留）",
        "blocks": [(rect(u - 0.03, v - 0.025, 0.06, 0.05), 1)],
        "areas": [rect(u - 0.03, v + 0.035, 0.06, 0.03)],
        "reserved": True,
    }

    # 放头像的框统一放大（长宽各乘 AREA_SCALE），中心不变。
    for item in items.values():
        item["areas"] = [scale_rect(a, AREA_SCALE) for a in item["areas"]]
    return items


AREA_SCALE = 1.3


def scale_rect(poly, k):
    us, vs = [p[0] for p in poly], [p[1] for p in poly]
    cu, cv = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    du, dv = (max(us) - min(us)) * k, (max(vs) - min(vs)) * k
    return rect(cu - du / 2, cv - dv / 2, du, dv)


def river():
    """小河：从左往右穿过校园下半部，在广场和图书馆、剧院之间。"""
    pts = [at(-0.90, 1.18), at(-0.50, 1.20), at(-0.15, 1.27), at(0.10, 1.24), at(0.40, 1.21), at(0.90, 1.27)]
    return pts


# ---------------------------------------------------------------- 画图

def prism(g, poly, floors, base=0, fill="#F2F2F2", edge="#9AA3AD"):
    h = floors * FLOOR
    z0 = base * FLOOR
    bottom = [iso(u, v, z0) for u, v in poly]
    top = [iso(u, v, z0 + h) for u, v in poly]
    n = len(poly)
    # 只画朝向屏幕的侧面（屏幕 y 往下的那些边）
    for i in range(n):
        j = (i + 1) % n
        if bottom[i][1] + bottom[j][1] > top[i][1] + top[j][1] - 1e-6 and (bottom[i][1] + bottom[j][1]) / 2 >= min(p[1] for p in bottom) + 0:
            g.polygon([bottom[i], bottom[j], top[j], top[i]], fill="#D9DDE2", outline=edge)
    g.polygon(top, fill=fill, outline=edge)


def screen_rect(poly):
    """平面上的矩形投影成菱形；取菱形里能放下的最大正放矩形（中心相同，宽高各一半）。"""
    pts = [iso(u, v) for u, v in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
    return (cx - w / 2, cy - h / 2, w, h)


def label_point(item):
    pts = []
    for block in item.get("blocks", []):
        poly, floors = block[0], block[1]
        base = block[2] if len(block) > 2 else 0
        pts += [iso(u, v, (floors + base) * FLOOR) for u, v in poly]
    for poly in item.get("ground", []):
        pts += [iso(u, v) for u, v in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return ((min(xs) + max(xs)) / 2, min(ys) - 18)


def diagram():
    items = layout()
    img = Image.new("RGB", (W, H), "#FFFFFF")
    g = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 22)
    # 校园地块和外面的马路
    g.rectangle([0, 0, W, H], fill="#E6E6E6")
    g.polygon([iso(0, 0), iso(L, 0), iso(L, L), iso(0, L)], fill="#EEF5E9", outline="#B8C4B0")
    # 河
    rv = river()
    g.line([iso(u, v) for u, v in rv], fill="#9CC9E8", width=40, joint="curve")
    # 地面上的场地
    for item in items.values():
        for poly in item.get("ground", []):
            g.polygon([iso(u, v) for u, v in poly], fill="#F7F1E3", outline="#C9B98F")
    # 楼：按离屏幕的远近排序，远的先画
    blocks = []
    for key, item in items.items():
        for block in item["blocks"]:
            poly = block[0]
            depth = sum(u + v for u, v in poly) / len(poly)
            blocks.append((depth, block))
    for _, block in sorted(blocks, key=lambda b: b[0]):
        prism(g, block[0], block[1], block[2] if len(block) > 2 else 0)
    # 放头像的区域
    for item in items.values():
        for a in item["areas"]:
            x, y, w, h = screen_rect(a)
            g.rectangle([x, y, x + w, y + h], outline="#E5484D", width=3)
    # 名字
    for item in items.values():
        x, y = label_point(item)
        tw = g.textlength(item["label"], font=font)
        g.rounded_rectangle([x - tw / 2 - 10, y - 16, x + tw / 2 + 10, y + 16], radius=14, fill="#1F2937")
        g.text((x - tw / 2, y - 14), item["label"], font=font, fill="#FFFFFF")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "campus-diagram.png"
    img.save(out)
    print(out.relative_to(ROOT))


def coords():
    out = {}
    for key, item in layout().items():
        x, y = label_point(item)
        out[key] = {
            "label": item["label"],
            "labelAt": [round(x / W, 4), round(y / H, 4)],
            "areas": [[round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)] for x, y, w, h in map(screen_rect, item["areas"])],
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))


MARGIN = 0.03  # 楼和场地离校园边界至少留这么多（平面坐标）


def check():
    """列出超出校园边界、或者被画面边缘裁掉的地点。"""
    bad = []
    for key, item in layout().items():
        polys = [b[0] for b in item["blocks"]] + item.get("ground", []) + item["areas"]
        for poly in polys:
            for u, v in poly:
                if not (MARGIN <= u <= L - MARGIN and MARGIN <= v <= L - MARGIN):
                    bad.append(f"{key}: 平面点 ({u:.3f}, {v:.3f}) 出了校园")
                    break
        pts = []
        for b in item["blocks"]:
            pts += [iso(u, v, (b[1] + (b[2] if len(b) > 2 else 0)) * FLOOR) for u, v in b[0]]
        for poly in item.get("ground", []) + item["areas"]:
            pts += [iso(u, v) for u, v in poly]
        lx, ly = label_point(item)
        pts += [(lx - 90, ly - 16), (lx + 90, ly + 16)]
        for x, y in pts:
            if not (8 <= x <= W - 8 and 8 <= y <= H - 8):
                bad.append(f"{key}: 屏幕点 ({x:.0f}, {y:.0f}) 出了画面")
                break
    # 头像框不能被任何楼挡住：把所有楼在画面上的轮廓画进一张蒙版，看框里有没有楼。
    mask = Image.new("L", (W, H), 0)
    mg = ImageDraw.Draw(mask)
    for item in layout().values():
        for b in item["blocks"]:
            base = b[2] if len(b) > 2 else 0
            for z in range(base * FLOOR, (base + b[1]) * FLOOR + 1, 2):
                mg.polygon([iso(u, v, z) for u, v in b[0]], fill=255)
    water = Image.new("L", (W, H), 0)
    ImageDraw.Draw(water).line([iso(u, v) for u, v in river()], fill=255, width=40 + 10, joint="curve")
    for key, item in layout().items():
        for a in item["areas"]:
            x, y, w, h = screen_rect(a)
            crop = water.crop((round(x), round(y), round(x + w), round(y + h)))
            if any(crop.get_flattened_data()):
                bad.append(f"{key}: 头像框压到了河")
    for key, item in layout().items():
        if item.get("areaOnRoof"):
            continue
        for a in item["areas"]:
            x, y, w, h = screen_rect(a)
            crop = mask.crop((round(x), round(y), round(x + w), round(y + h)))
            covered = sum(1 for p in crop.get_flattened_data() if p) / max(1, crop.width * crop.height)
            if covered > 0.02:
                bad.append(f"{key}: 头像框有 {covered:.0%} 被楼挡住")
    print("\n".join(dict.fromkeys(bad)) or "全部在校园里、也都在画面里，头像框也没被楼挡住")
    return not bad


# ---------------------------------------------------------------- 上色草图和出图

COLORS = {  # (屋顶, 墙)
    "senior": ("#8FA9D6", "#EEE7D9"),
    "junior": ("#E59A6B", "#F4E4D0"),
    "primary": ("#F5C451", "#FFF2D8"),
    "club": ("#6FB3A3", "#CDE7E0"),
    "library": ("#E3D9C3", "#F2ECDF"),
    "theatre": ("#CDB78A", "#E8DCBF"),
    "shop": ("#E26D6D", "#FBE5E5"),
    "gate": ("#8C6E54", "#B89A7E"),
    "playground": ("#B9B2A6", "#D6D0C6"),
}
GROUND = {"plaza": "#EFE6CF", "playground": "#D66A4A", "basketball": "#E59650"}


def paths():
    """步道：校门过桥到广场，广场连到各处。"""
    return [
        [at(0.0, 1.74), at(0.0, 1.36), at(-0.03, 1.02)],  # 主路（过河处是桥）
        [at(-0.15, 0.88), at(-0.40, 0.98)],  # 广场 -> 小学部
        [at(-0.10, 0.76), at(-0.26, 0.62)],  # 广场 -> 高中部
        [at(0.00, 0.76), at(0.08, 0.60)],  # 广场 -> 初中部
        [at(0.06, 0.90), at(0.26, 0.96)],  # 广场 -> 社团活动中心
        [at(0.40, 0.70), at(0.42, 0.56)],  # 社团活动中心 -> 操场
        [at(0.0, 1.50), at(-0.30, 1.45)],  # 主路 -> 图书馆
        [at(0.0, 1.55), at(0.26, 1.52)],  # 主路 -> 剧院
    ]


def sketch():
    items = layout()
    img = Image.new("RGB", (W, H), "#8C9198")  # 校外的马路
    g = ImageDraw.Draw(img)
    g.polygon([iso(0, 0), iso(L, 0), iso(L, L), iso(0, L)], fill="#DCD7CC")  # 人行道
    m = 0.02
    g.polygon([iso(m, m), iso(L - m, m), iso(L - m, L - m), iso(m, L - m)], fill="#9ED07F")  # 草地
    for line in paths():
        g.line([iso(u, v) for u, v in line], fill="#E8E3D7", width=22, joint="curve")
    g.line([iso(u, v) for u, v in river()], fill="#E3DCCB", width=64, joint="curve")  # 河岸步道
    g.line([iso(u, v) for u, v in river()], fill="#7EC3E6", width=40, joint="curve")
    pu0, pv0 = at(-0.30, 1.72)
    g.polygon([iso(pu0 - 0.06, pv0 - 0.04), iso(pu0 + 0.06, pv0 - 0.04), iso(pu0 + 0.06, pv0 + 0.04), iso(pu0 - 0.06, pv0 + 0.04)], fill="#A3A7AD")  # 停车场
    for k in range(-5, 6):
        g.line([iso(pu0 + k * 0.01, pv0 - 0.04), iso(pu0 + k * 0.01, pv0 - 0.01)], fill="#FFFFFF", width=2)
        g.line([iso(pu0 + k * 0.01, pv0 + 0.01), iso(pu0 + k * 0.01, pv0 + 0.04)], fill="#FFFFFF", width=2)
    bu, bv = at(0.0, 1.245)
    g.polygon([iso(bu - 0.012, bv - 0.035), iso(bu + 0.012, bv - 0.035), iso(bu + 0.012, bv + 0.035), iso(bu - 0.012, bv + 0.035)], fill="#C9A27A")  # 桥
    for key, item in items.items():
        for poly in item.get("ground", []):
            g.polygon([iso(u, v) for u, v in poly], fill=GROUND.get(key, "#EFE6CF"))
    pu, pv = at(0.42, 0.44)
    g.polygon([iso(u, v) for u, v in stadium(pu, pv, 0.20, 0.10)], fill="#6DBE5A")  # 足球场草皮
    blocks = []
    for key, item in items.items():
        for block in item["blocks"]:
            depth = sum(u + v for u, v in block[0]) / len(block[0])
            blocks.append((depth, key, block))
    for _, key, block in sorted(blocks, key=lambda b: b[0]):
        roof, wall = COLORS.get(key, ("#DDDDDD", "#EEEEEE"))
        base = block[2] if len(block) > 2 else 0
        h, z0 = block[1] * FLOOR, base * FLOOR
        bottom = [iso(u, v, z0) for u, v in block[0]]
        top = [iso(u, v, z0 + h) for u, v in block[0]]
        n = len(bottom)
        for i in range(n):
            j = (i + 1) % n
            g.polygon([bottom[i], bottom[j], top[j], top[i]], fill=wall)
        g.polygon(top, fill=roof)
    decorate(img, items)
    out = OUT / "campus-sketch.png"
    img.save(out)
    print(out.relative_to(ROOT))
    return out


def decorate(img, items):
    """在空草地上撒树丛。避开楼、场地、路、河和头像框，头像框里必须保持空着。"""
    import random

    rnd = random.Random(7)
    keep = Image.new("L", (W, H), 0)
    kg = ImageDraw.Draw(keep)
    m = 0.05
    kg.polygon([iso(m, m), iso(L - m, m), iso(L - m, L - m), iso(m, L - m)], fill=255)
    block = Image.new("L", (W, H), 0)
    bg = ImageDraw.Draw(block)
    for line in paths():
        bg.line([iso(u, v) for u, v in line], fill=255, width=40, joint="curve")
    bg.line([iso(u, v) for u, v in river()], fill=255, width=90, joint="curve")
    pu0, pv0 = at(-0.30, 1.72)
    bg.polygon([iso(pu0 - 0.07, pv0 - 0.05), iso(pu0 + 0.07, pv0 - 0.05), iso(pu0 + 0.07, pv0 + 0.05), iso(pu0 - 0.07, pv0 + 0.05)], fill=255)
    for item in items.values():
        for b in item["blocks"]:
            base = b[2] if len(b) > 2 else 0
            for z in range(0, (base + b[1]) * FLOOR + 1, 4):
                bg.polygon([iso(u, v, z) for u, v in b[0]], fill=255)
            bg.polygon([iso(u, v) for u, v in scale_rect(b[0], 1.25)] if len(b[0]) == 4 else [iso(u, v) for u, v in b[0]], fill=255)
        for poly in item.get("ground", []):
            bg.polygon([iso(u, v) for u, v in scale_rect(poly, 1.15)], fill=255)
        for a in item["areas"]:
            x, y, w, h = screen_rect(a)
            bg.rectangle([x - 20, y - 20, x + w + 20, y + h + 20], fill=255)
        lx, ly = label_point(item)
        bg.rectangle([lx - 100, ly - 25, lx + 100, ly + 25], fill=255)
    g = ImageDraw.Draw(img)
    trees = []
    for _ in range(4000):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.uniform(7, 12)
        if not keep.getpixel((int(x), int(y))) or block.getpixel((int(x), int(y))):
            continue
        if any((x - tx) ** 2 + (y - ty) ** 2 < (r + tr + 6) ** 2 for tx, ty, tr in trees):
            continue
        trees.append((x, y, r))
        if len(trees) >= 170:
            break
    for x, y, r in sorted(trees, key=lambda t: t[1]):
        g.ellipse([x - r * 0.25, y - r * 0.2, x + r * 0.25, y + r * 0.9], fill="#7A5A3A")
        g.ellipse([x - r, y - 2 * r, x + r, y], fill="#4E9A47")


PROMPT = (
    "这是一张校园的等距布局草图。请把它画成精美的插画，严格按照草图的构图：每栋建筑、每块场地、小河和道路的位置、大小、形状和朝向都和草图完全一样，"
    "视角也和草图一样（等距 45 度俯视）。画风是商业图库里常见的等距扁平矢量城市插画：色块干净平整，建筑有清晰的明暗两个侧面，"
    "窗户、空调外机、太阳能板、屋顶绿化、行道树、长椅、路灯、停车位等小细节非常丰富，配色清新明亮。"
    "画面内容是一所学校的校园，白天，阳光明媚：\n"
    "- 左上角蓝灰屋顶的工字型大楼是高中部教学楼，7 层，比例修长挺拔，米白墙，蓝色玻璃窗排列整齐，楼顶有太阳能板、空调外机和水箱，门前有旗杆和自行车棚，两个院子里铺着浅色地砖、种着几棵树。\n"
    "- 上方中间橙色屋顶的丁字型大楼是初中部教学楼，6 层，暖白墙配橙色线条，楼顶有绿化。\n"
    "- 左边黄色屋顶的 L 型矮楼是小学部，3 层，墙面活泼，有彩色的窗框，院子里有小滑梯和花坛。\n"
    "- 右边两栋青绿色的高楼是社团活动中心，参考新加坡国家图书馆：两栋高低不同的现代高层建筑（一栋十几层、一栋十层左右），外立面有一层层的水平遮阳板和大面积玻璃，两栋之间有一条高空连廊，楼间是通透的中庭。\n"
    "- 中间米色的圆形是中心广场，铺着同心圆花纹的地砖，中间空着，边上一圈有长椅、路灯、花坛和几棵树。\n"
    "- 右上方是大学标准的 400 米红色塑胶跑道，白色分道线，中间是绿色足球场和两个球门，一侧有带顶棚的看台。旁边橙色的是篮球场，有场地线和篮架，四周有围网。\n"
    "- 一条蓝色的小河从左到右穿过校园，河岸有石砌护岸和步道，主路上有一座木桥过河，河上漂着一两条小船。\n"
    "- 河南边左侧浅色的椭圆形建筑是图书馆，参考新加坡 The Star Vista：有机的流线型外形，一层层退台上种满绿植，中间是一个露天的半圆形阶梯剧场。\n"
    "- 河南边右侧是剧院，参考新加坡滨海艺术中心（Esplanade）：两个低矮的半球形玻璃圆顶，圆顶表面覆盖着由许多小三角形铝制遮阳板拼成的整齐格纹，颜色是浅金属银灰色，表面是光滑的曲面，不是尖刺，也不是刺球；圆顶在河边，前面有临水的台阶广场。\n"
    "- 剧院旁边红色屋顶的小房子是小卖部，一层，门口有条纹遮阳棚和几张小桌子。\n"
    "- 最下方中间是学校的大门，两根门柱，旁边有一块公告栏。浅色的线是校园里的步道，深绿色的小圆点是一棵棵树，校门左边灰色的是停车场，停着几辆小汽车。河两岸有浅色的步道和栏杆。\n"
    "- 四个角上灰色的部分是校外的马路，路上有几辆小汽车和公交车，路边有行道树。\n"
    "画面里没有任何人物，没有任何文字、字母、数字和图标标记。"
)


def graph2(image1, image2, prompt, seed):
    import scenes  # noqa: E402  同目录

    g = scenes.workflow(image1, prompt, seed)
    g["15"] = {"class_type": "LoadImage", "inputs": {"image": image2}}
    for k in ("5", "6"):
        g[k]["inputs"]["image2"] = ["15", 0]
    g["14"]["inputs"]["filename_prefix"] = "sfb_campus"
    return g


def render(seeds):
    import scenes

    sk = sketch()
    style = Path(r"F:\Project\schoolforbots\素材\参考\扁平风2.webp")
    scenes.COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    (scenes.COMFY_INPUT / "sfb_campus_sketch.png").write_bytes(sk.read_bytes())
    Image.open(style).convert("RGB").save(scenes.COMFY_INPUT / "sfb_style_flat2.png")
    raw = ROOT / "sources" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for seed in seeds:
        out = raw / f"campus-flat-{seed}.png"
        # 只给草图，不给参考图：给了参考图模型会照抄参考图的内容。
        out.write_bytes(scenes.comfy("sfb_campus_sketch.png", PROMPT, seed))
        print(out.relative_to(ROOT), flush=True)


# ---------------------------------------------------------------- 定稿插画上的实测坐标

FINAL = "sources/raw/campus-flat-7-r45.png"  # 定稿的白天插画（种子 7，精修 0.45）

# 在定稿插画上实测、校准过的位置（像素，画面 1664×1040）。模型没有完全照草图画，所以以这里为准。
# labelAt 是名字标签的中心点；areas 是放头像的框 [x, y, 宽, 高]。
MEASURED = {
    "senior": {"labelAt": (265, 52), "areas": [(240, 255, 190, 90)]},
    "junior": {"labelAt": (985, 42), "areas": [(895, 245, 180, 72)]},
    "primary": {"labelAt": (245, 368), "areas": [(150, 480, 175, 85)]},
    "plaza": {"labelAt": (775, 368), "areas": [(660, 415, 205, 100)]},
    "club": {"labelAt": (1165, 292), "areas": [(1150, 385, 178, 88)]},  # 压在两栋楼和连廊上
    "playground": {"labelAt": (1345, 42), "areas": [(1240, 165, 150, 70)]},
    "basketball": {"labelAt": (1495, 283), "areas": [(1435, 330, 125, 60)]},
    "library": {"labelAt": (395, 692), "areas": [(325, 785, 95, 50)]},
    "theatre": {"labelAt": (1245, 700), "areas": [(1110, 845, 105, 50)]},
    "shop": {"labelAt": (1005, 770), "areas": [(945, 862, 70, 30)]},  # 往右挪一点，标签和校门、剧院隔得差不多远
    "gate": {"labelAt": (845, 890), "areas": []},  # 没有头像区域，标签贴在校门楼顶上方
}
LABELS = {
    "senior": "高中部", "junior": "初中部", "primary": "小学部", "plaza": "广场", "club": "社团活动中心",
    "playground": "操场", "basketball": "篮球场", "library": "图书馆", "theatre": "剧院", "shop": "小卖部", "gate": "校门",
}
RESERVED = {"playground", "basketball", "library", "theatre", "shop"}


LABEL_GAP = 4  # 标签底边和头像区域上沿之间留的空（像素）


def final_locations():
    """清单里 campus.locations 的内容：比例坐标，一个地点一个 area（取第一个框）。
    labelAt 是名字标签底边的中点：有头像区域的，紧贴在区域正上方；没有的（校门）用 MEASURED 里的点。"""
    out = {}
    for key, m in MEASURED.items():
        x, y = m["labelAt"]
        if m["areas"]:
            ax, ay, aw, ah = m["areas"][0]
            x, y = ax + aw / 2, ay - LABEL_GAP
        loc = {"label": LABELS[key], "labelAt": [round(x / W, 4), round(y / H, 4)]}
        areas = [[round(a / W, 4), round(b / H, 4), round(c / W, 4), round(d / H, 4)] for a, b, c, d in m["areas"]]
        loc["area"] = areas[0] if areas else None
        if key in RESERVED:
            loc["reserved"] = True
        out[key] = loc
    return out


def final_overlay(image, out):
    im = Image.open(image).convert("RGB")
    g = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 20)
    for key, loc in final_locations().items():
        if loc["area"]:
            x, y, w, h = loc["area"]
            g.rectangle([x * W, y * H, (x + w) * W, (y + h) * H], outline="#FF2D55", width=3)
        lx, ly = loc["labelAt"][0] * W, loc["labelAt"][1] * H
        tw = g.textlength(loc["label"], font=font)
        g.rounded_rectangle([lx - tw / 2 - 10, ly - 30, lx + tw / 2 + 10, ly], radius=14, fill="#1F2937")
        g.text((lx - tw / 2, ly - 28), loc["label"], font=font, fill="#FFFFFF")
    im.save(out)
    print(out)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        sys.path.insert(0, str(Path(__file__).parent))
        render([int(x) for x in sys.argv[2:]] or [1, 2, 3])
    else:
        {"diagram": diagram, "coords": coords, "check": check, "sketch": sketch}[cmd]()
