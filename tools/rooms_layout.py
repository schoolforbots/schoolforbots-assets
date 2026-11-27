"""室内场景的布局：教室（阶梯教室）、社团大厅（6 张斗地主牌桌）、牌桌近景。等距视角，和校园全景一致。

  python tools/rooms_layout.py diagram [场景...]   白模示意图 -> sources/layouts/<场景>-diagram.png
  python tools/rooms_layout.py check [场景...]     检查座位和区域有没有出画面、有没有被挡住

房间在平面上是 0–1 的正方形。u 往屏幕右下走，v 往屏幕左下走，(0, 0) 是房间最里面的墙角。
两面后墙沿 u=0（左后墙）和 v=0（右后墙）立起来。
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sources" / "layouts"
W, H = 1664, 1040
A = 780  # 平面边长 1 投影后的半宽
CX, Y0 = W / 2, 250  # 房间最里面墙角（地面）的位置
WALL = 220  # 墙上东西（黑板、窗户、牌匾）按这个高度摆（像素）
WALL_DRAW = 720  # 墙实际画多高：一直伸出画面顶上，不留白
EXT = 0.62  # 地板和墙往画面外多铺这么多（平面坐标），左右两角和下边都不留白
STEP = 7  # 阶梯教室每升一排的高度（像素）
FONT = "C:/Windows/Fonts/msyh.ttc"


def iso(u, v, z=0.0):
    return (CX + (u - v) * A, Y0 + (u + v) * A / 2 - z)


def rect(u, v, du, dv):
    return [(u, v), (u + du, v), (u + du, v + dv), (u, v + dv)]


def ellipse(u, v, r, n=36):
    return [(u + r * math.cos(t), v + r * math.sin(t)) for t in (2 * math.pi * i / n for i in range(n))]


# ---------------------------------------------------------------- 三个场景

def classroom():
    """阶梯教室：黑板在右后墙（v=0），讲台在黑板前，8 排长桌朝向黑板，越往后越高，中间一条过道。"""
    rows = []
    blocks = [(rect(0.38, 0.07, 0.24, 0.07), 0, 12, "#B98B5E")]  # 讲台
    halves = [(0.07, 0.46), (0.54, 0.93)]  # 过道左右两半
    for i in range(8):
        v = 0.30 + i * 0.085
        z = i * STEP
        if i:
            blocks.append((rect(0.03, v - 0.035, 0.94, 0.085), 0, z, "#CFC6B6"))  # 这一排的台阶（从地面砌上来，侧面看得见）
        blocks.append((rect(0.46, v - 0.035, 0.08, 0.085), z, 0.5, "#B5525A"))  # 这一排的过道红地毯
        for u0, u1 in halves:
            blocks.append((rect(u0, v, u1 - u0, 0.024), z, 11, "#C8915A"))  # 长桌
            n = 8 if u0 < 0.5 else 7  # 每排 15 个座位：左 8 右 7
            for k in range(n):
                cu = u0 + (u1 - u0) * (k + 0.5) / n
                blocks.append((rect(cu - 0.016, v + 0.036, 0.032, 0.028), z, 7, "#3F6FB5"))  # 椅子
            # 学生坐在桌子后面，头像底边落在这条线上；左右两半各一段
            a, b = iso(u0 + 0.01, v + 0.05, z + 6), iso(u1 - 0.01, v + 0.05, z + 6)
            rows.append([round(a[0]), round(a[1]), round(b[0]), round(b[1]), n])
    return {
        "label": "教室（阶梯教室）",
        "walls": {"left": "#EFE7DA", "right": "#F5EFE5"},
        "floor": "#C9A57E",
        "wallItems": [
            ("right", 0.24, 0.76, 0.22, 0.70, "#2F5D46"),  # 黑板
            ("right", 0.30, 0.70, 0.76, 0.98, "#F7F7F7"),  # 黑板上方卷起来的投影幕
            ("right", 0.84, 0.90, 0.60, 0.80, "#333333"),  # 挂钟
            ("right", 0.04, 0.16, 0.80, 0.95, "#E3E3E3"),  # 空调
        ],
        "windows": [("left", 0.12, 0.88)],
        "blocks": blocks,
        "ordered": True,  # 按加进去的顺序画（一排一排从后往前），不按远近排序
        "points": {"teacher": iso(0.50, 0.17, 0)},
        "rows": rows,
        "capacity": "8 排，每排左 8 右 7，共 120 个座位",
    }


def inv(x, y, z=0.0):
    """屏幕坐标 + 高度 -> 平面坐标。"""
    y = y + z
    d, s_ = (x - CX) / A, (y - Y0) * 2 / A
    return ((s_ + d) / 2, (s_ - d) / 2)


def chairs(seats, height, size=0.045):
    """在每个座位下面放一把椅子（草图里画出来，模型就不会自己多补椅子）。"""
    out = []
    for x, y in seats:
        u, v = inv(x, y, height)
        out.append((rect(u - size / 2, v - size / 2, size, size), 0, 9, "#8B5A2B"))
    return out


def _table(u, v, r, height, k=1.45):
    """圆牌桌的三个座位，按画面上的角度绕桌子放：0 左前、1 后、2 右前，相隔 120°。
    观战区在桌子正前方（画面下方）。返回（座位的屏幕坐标, 观战区的屏幕矩形）。"""
    cx, cy = iso(u, v, height)
    rx, ry = r * A * math.sqrt(2) * k, r * A * math.sqrt(2) / 2 * k
    seats = [(cx + rx * math.cos(math.radians(t)), cy - ry * math.sin(math.radians(t))) for t in (210, 90, 330)]
    w, h = rx * 1.3, ry * 0.7
    spect = (cx - w / 2, cy + ry * 1.25, w, h)
    return seats, spect


def club_hall():
    """社团活动中心里的斗地主活动室：6 张圆牌桌，2 排 × 3。"""
    blocks, seats, spectators = [], [], []
    r = 0.065
    for v in (0.32, 0.68):
        for u in (0.22, 0.50, 0.78):
            blocks.append((ellipse(u, v, r), 0, 14, "#2E7D4F"))
            s, sp = _table(u, v, r, 14)
            blocks += chairs(s, 14, 0.035)
            seats.append([[round(x), round(y)] for x, y in s])
            spectators.append(sp)
    return {
        "label": "社团大厅（6 张牌桌）",
        "walls": {"left": "#EFE6D8", "right": "#F5EDE0"},
        "floor": "#D8B98F",
        "wallItems": [("right", 0.35, 0.65, 0.55, 0.80, "#D9B44A")],  # 社团牌匾
        "windows": [("left", 0.15, 0.85)],
        "blocks": blocks,
        "tables": seats,
        "spectatorAreas": spectators,
    }


def club_table():
    """斗地主牌桌近景：一张大圆桌，三个座位，桌前一块观战区。"""
    u, v, r = 0.50, 0.50, 0.20
    seats, spect = _table(u, v, r, 24, k=1.35)
    return {
        "label": "牌桌近景",
        "walls": {"left": "#EFE6D8", "right": "#F5EDE0"},
        "floor": "#D8B98F",
        "wallItems": [],
        "windows": [("left", 0.20, 0.80)],
        "blocks": [(ellipse(u, v, r), 0, 24, "#2E7D4F")] + chairs(seats, 24, 0.08),
        "points": {"pile": iso(u, v, 24)},
        "tables": [[[round(x), round(y)] for x, y in seats]],
        "spectatorAreas": [spect],
    }


SCENES = {"classroom": classroom, "club-hall": club_hall, "club-table": club_table}


# ---------------------------------------------------------------- 画图

def wall_poly(side, a, b, z0, z1):
    if side == "right":  # 沿 v=0，u 从 a 到 b
        return [iso(a, 0, z0), iso(b, 0, z0), iso(b, 0, z1), iso(a, 0, z1)]
    return [iso(0, a, z0), iso(0, b, z0), iso(0, b, z1), iso(0, a, z1)]  # 沿 u=0


def prism(g, poly, base, height, color):
    bottom = [iso(u, v, base) for u, v in poly]
    top = [iso(u, v, base + height) for u, v in poly]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        g.polygon([bottom[i], bottom[j], top[j], top[i]], fill=shade(color), outline="#8C8C8C")
    g.polygon(top, fill=color, outline="#8C8C8C")


def shade(hex_color, k=0.82):
    r, gg, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * k):02X}{int(gg * k):02X}{int(b * k):02X}"


def screen_rect(poly):
    pts = [iso(u, v) for u, v in poly]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
    return (cx - w / 2, cy - h / 2, w, h)


def draw(name, d, labels=True, markers=True):
    img = Image.new("RGB", (W, H), "#FFFFFF")
    g = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 22)
    e = 1 + EXT
    g.polygon(wall_poly("left", 0, e, 0, WALL_DRAW), fill=d["walls"]["left"])
    g.polygon(wall_poly("right", 0, e, 0, WALL_DRAW), fill=d["walls"]["right"])
    g.line([iso(0, 0), iso(0, 0, WALL_DRAW)], fill="#C9C2B6", width=2)  # 墙角
    g.polygon([iso(0, 0), iso(e, 0), iso(e, e), iso(0, e)], fill=d["floor"])
    for side in ("left", "right"):  # 踢脚线
        g.polygon(wall_poly(side, 0, e, 0, 8), fill=shade(d["walls"][side], 0.85))
    if "aisle" in d:
        poly, color = d["aisle"]
        g.polygon([iso(u, v) for u, v in poly], fill=color)
    for side, a, b in d.get("windows", []):
        n = 3
        for k in range(n):
            s = a + (b - a) * k / n + 0.03
            e = a + (b - a) * (k + 1) / n - 0.03
            g.polygon(wall_poly(side, s, e, WALL * 0.3, WALL * 0.85), fill="#BFE3F5", outline="#8FB8CC")
    for side, a, b, z0, z1, color in d.get("wallItems", []):
        g.polygon(wall_poly(side, a, b, WALL * z0, WALL * z1), fill=color, outline="#555555")
    order = d["blocks"] if d.get("ordered") else sorted(d["blocks"], key=lambda b: sum(u + v for u, v in b[0]) / len(b[0]))
    for poly, base, height, color in order:
        prism(g, poly, base, height, color)
    if not markers:
        return img
    red = "#E5484D"
    for row in d.get("rows", []):
        g.line(row[:4], fill=red, width=4)
    for seats in d.get("tables", []):
        for i, (x, y) in enumerate(seats):
            rr = 16 if name == "club-hall" else 34
            g.ellipse([x - rr, y - rr, x + rr, y + rr], outline=red, width=3)
            if labels:
                g.text((x - 6, y - 14), str(i), font=font, fill=red)
    for sp in d.get("spectatorAreas", []):
        x, y, w, h = sp
        g.rectangle([x, y, x + w, y + h], outline="#2B7FFF", width=3)
    for key, (x, y) in d.get("points", {}).items():
        rr = 30 if key == "teacher" else 18
        g.ellipse([x - rr, y - rr * 2, x + rr, y], outline=red if key == "teacher" else "#2B7FFF", width=4)
    if labels:
        g.rounded_rectangle([20, 20, 20 + g.textlength(d["label"], font=font) + 24, 56], radius=16, fill="#1F2937")
        g.text((32, 24), d["label"], font=font, fill="#FFFFFF")
    return img


def diagram(names):
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names:
        out = OUT / f"{name}-diagram.png"
        draw(name, SCENES[name]()).save(out)
        print(out.relative_to(ROOT))


def check(names):
    bad = []
    for name in names:
        d = SCENES[name]()
        pts = [(x, y) for row in d.get("rows", []) for x, y in (row[0:2], row[2:4])]
        pts += [tuple(p) for seats in d.get("tables", []) for p in seats]
        pts += list(d.get("points", {}).values())
        for x, y in pts:
            if not (30 <= x <= W - 30 and 30 <= y <= H - 30):
                bad.append(f"{name}: 点 ({x:.0f}, {y:.0f}) 太靠近画面边缘")
        for sp in d.get("spectatorAreas", []):
            x, y, w, h = sp
            if x < 0 or y < 0 or x + w > W or y + h > H:
                bad.append(f"{name}: 观战区出了画面")
        img = draw(name, d, labels=False)
        white = sum(1 for p in img.get_flattened_data() if p == (255, 255, 255))
        if white:
            bad.append(f"{name}: 画面里还有 {white} 个空白像素")
    print("\n".join(bad) or "全部在画面里，画面也没有留白")
    return not bad


# ---------------------------------------------------------------- 出图

STYLE = (
    "画风是商业图库里常见的等距扁平矢量插画（和学校全景图同一个风格）：色块干净平整，物体有清晰的明暗两个侧面，"
    "小细节丰富，配色清新明亮，室内光线柔和温暖。画面里没有任何人物，没有任何文字、字母和数字。"
)
KEEP = (
    "请严格按照这张等距草图的构图画：墙、地板、每件家具的位置、大小、形状和朝向都和草图完全一样，视角也一样（等距 45 度俯视），"
    "房间要和草图一样大：两面墙一直延伸到画面最上边，地板一直铺到画面的左边、右边和下边，画面四个角都是墙或地板，"
    "绝对不要把房间画小，不要画房间外面的空白、底色或地基边缘。"
)
PROMPTS = {
    "classroom": (
        "把这张草图画成一间温馨明亮的大学阶梯教室。右边那面墙上深绿色的是一块大黑板（黑板上空白，不写字），黑板上方是卷起来的白色投影幕，"
        "黑板右边有一个挂钟，墙角上方有一台空调。黑板前棕色的是老师的木制讲台，讲台上有一台笔记本电脑、一个话筒和一个水杯。"
        "左边那面墙上浅蓝色的是三扇大窗户，窗外是蓝天和绿树，阳光斜斜地照进来，窗台上有小盆栽。"
        "地面是一级一级往后升高的阶梯，每一级的侧面清楚可见；每一级上有一排长长的木制课桌，课桌后面是一排蓝色的座椅，座椅上是空的。"
        "中间一条铺着红地毯的过道把每排分成左右两半。课桌上零星放着书、笔记本和笔。墙上挂着几张彩色的学科海报（海报上不写字），屋顶有一排排吸顶灯。"
    ),
    "club-hall": (
        "把这张草图画成学校社团活动中心里一间温馨的棋牌活动室。右边那面墙上金色的是一块空白的木牌匾（牌匾上不写字），"
        "墙边有书架、桌游柜和绿植。左边那面墙上浅蓝色的是三扇大窗户。"
        "地上六个深绿色的圆形是六张铺着绿色绒布的圆牌桌，每张桌上放着几叠扑克牌和筹码。每张桌子周围只有三把空着的木椅：左边一把、后面一把、右边一把，"
        "桌子正前方（靠近画面下方的一侧）没有椅子，空着留给观战的人站。木地板，屋顶有暖色的吊灯。"
    ),
    "club-table": (
        "把这张草图画成学校棋牌活动室里一张斗地主牌桌的近景。中间深绿色的大圆是一张铺着绿色绒布的圆牌桌，"
        "桌面正中间摊开一小叠扑克牌，桌边放着几摞彩色筹码和一个计分小本子。桌子周围一共只有三把空着的木椅：左边一把、后面一把、右边一把，"
        "桌子正前方（靠近画面下方的一侧）没有椅子，一共只有三把椅子，不要画第四把，前面空着留给观战的人站。左边墙上浅蓝色的是三扇窗户，墙边有绿植和小柜子，木地板，桌子正上方有一盏暖色的吊灯。"
    ),
}


def sketch(name):
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{name}-sketch.png"
    draw(name, SCENES[name](), labels=False, markers=False).save(out)
    return out


def render(name, seeds):
    sys.path.insert(0, str(Path(__file__).parent))
    import scenes

    sk = sketch(name)
    image = f"sfb_room_{name}.png"
    scenes.COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    (scenes.COMFY_INPUT / image).write_bytes(sk.read_bytes())
    raw = ROOT / "sources" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    prompt = KEEP + PROMPTS[name] + STYLE
    for seed in seeds:
        out = raw / f"{name}-flat-{seed}.png"
        out.write_bytes(scenes.comfy(image, prompt, seed))
        print(out.relative_to(ROOT), flush=True)


def render_i2i(name, seeds, denoise):
    """从草图本身出发重画（图生图）：铺色和构图跟着草图走，房间不会被画小。"""
    sys.path.insert(0, str(Path(__file__).parent))
    import scenes

    sk = sketch(name)
    image = f"sfb_room_{name}.png"
    (scenes.COMFY_INPUT / image).write_bytes(sk.read_bytes())
    prompt = PROMPTS[name].replace("把这张草图画成", "") + STYLE
    raw = ROOT / "sources" / "raw"
    for seed in seeds:
        out = raw / f"{name}-i2i{int(denoise * 100)}-{seed}.png"
        out.write_bytes(scenes.comfy(image, prompt, seed, scenes.refine_workflow(image, prompt, seed, denoise)))
        print(out.relative_to(ROOT), flush=True)


# ---------------------------------------------------------------- 定稿插画上的实测坐标

# 定稿插画（像素坐标，画面 1664×1040）。模型没有完全照草图画，所以清单以这里为准。
FINAL = {
    "classroom": "sources/raw/classroom-i2i70-1.png",
    "club-hall": "sources/raw/club-hall-i2i70-1.png",
    "club-table": "sources/raw/club-table-i2i70-1-3chairs-2.png",
}

# 教室：每排椅子的中心线（按蓝色椅子自动检测，见 detect_rows），头像中心沿线均匀排开。
CLASSROOM_ROWS = [
        (620, 416, 872, 542, 8),  # 第 1 排左半
        (547, 435, 818, 570, 8),  # 第 2 排左半
        (503, 467, 769, 600, 8),  # 第 3 排左半
        (452, 500, 717, 632, 8),  # 第 4 排左半
        (379, 521, 661, 662, 8),  # 第 5 排左半
        (317, 550, 606, 694, 8),  # 第 6 排左半
        (252, 576, 535, 717, 8),  # 第 7 排左半
        (187, 601, 472, 744, 8),  # 第 8 排左半
        (1016, 590, 1262, 713, 7),  # 第 1 排右半
        (966, 625, 1207, 746, 7),  # 第 2 排右半
        (911, 660, 1149, 778, 7),  # 第 3 排右半
        (852, 692, 1090, 811, 7),  # 第 4 排右半
        (793, 726, 1028, 844, 7),  # 第 5 排右半
        (728, 756, 971, 878, 7),  # 第 6 排右半
        (646, 773, 913, 906, 7),  # 第 7 排右半
        (578, 797, 851, 934, 7),  # 第 8 排右半
]
CLASSROOM_TEACHER = (1130, 400)  # 讲台后面

# 社团大厅：6 张桌子的中心（按绿色桌面检测）。每张桌子的椅子摆法一样：左后、右后、左前，右前方空着给观战的人。
HALL_TABLES = [(750, 434), (963, 548), (480, 579), (1187, 668), (692, 694), (915, 810)]
HALL_SEATS = [(-95, -18), (68, -22), (-90, 50)]  # 相对桌子中心：0 左后、1 右后、2 左前
HALL_SPECTATORS = (20, 62, 80, 34)  # 相对桌子中心的观战区 [dx, dy, 宽, 高]

# 牌桌近景：0 左、1 后、2 右。
TABLE_SEATS = [(555, 630), (835, 470), (1120, 625)]
TABLE_PILE = (835, 590)
TABLE_SPECTATORS = (690, 815, 290, 70)

AVATAR = {"classroom": 0.016, "club-hall": 0.022, "club-table": 0.05}  # 建议的头像直径，占图宽的比例
KEYS = {"classroom": "classroom", "club-hall": "clubHall", "club-table": "clubTable"}
TIMES = {"morning": "06:00-12:00", "afternoon": "12:00-18:00", "evening": "18:00-06:00"}


def detect_rows(src):
    """按蓝色椅子找每排的中心线：先按过道的红地毯分成左右两半，再沿排的方向投影找峰。"""
    import numpy as np

    a = np.asarray(Image.open(src).convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    yy, xx = np.mgrid[0 : a.shape[0], 0 : a.shape[1]]
    blue = (b > 130) & (b - r > 60) & (b - g > 20) & (r < 120) & (yy > 380)
    red = (r > 150) & (r - g > 80) & (r - b > 70) & (yy > 380)
    U = xx + 2 * yy  # 沿过道方向不变
    c = np.median(U[red])
    out = {}
    for side, mask in (("left", blue & (U < c - 20)), ("right", blue & (U > c + 20))):
        ys, xs = np.nonzero(mask)
        p = ys - 0.5 * xs  # 沿排的方向不变
        edges = np.arange(p.min() - 20, p.max() + 22, 2)
        hist, _ = np.histogram(p, bins=edges)
        hs = np.convolve(hist, np.ones(9) / 9, mode="same")
        rows = []
        for i in range(len(hs)):
            if hs[i] == hs[max(0, i - 12) : i + 13].max() and hs[i] > hs.max() * 0.2:
                cc = edges[i] + 1
                X = xs[np.abs(p - cc) < 8]
                x1, x2 = np.percentile(X, 1), np.percentile(X, 99)
                if x2 - x1 > 100:
                    rows.append([int(x1), int(round(cc + 0.5 * x1)), int(x2), int(round(cc + 0.5 * x2))])
        out[side] = rows
    return out


def final_data(name):
    """清单里 rooms.<场景> 的内容，比例坐标。"""
    pt = lambda x, y: [round(x / W, 4), round(y / H, 4)]
    box = lambda x, y, w, h: [round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)]
    image = f"rooms/{name}.webp"
    d = {
        "width": W,
        "height": H,
        "scenes": {t: {"image": image, "hours": h} for t, h in TIMES.items()},
        "avatarSize": AVATAR[name],
    }
    if name == "classroom":
        d["teacher"] = pt(*CLASSROOM_TEACHER)
        d["rows"] = [{"from": pt(x1, y1), "to": pt(x2, y2), "seats": n} for x1, y1, x2, y2, n in CLASSROOM_ROWS]
        d["$rows"] = "每段是一排椅子的中心线，学生头像的中心沿线均匀排开（第 k 个在 (k+0.5)/seats 处）。前 8 段是过道左边（每排 8 座），后 8 段是右边（每排 7 座），共 120 座。坐不下的收成 +N。"
    elif name == "club-hall":
        d["tables"] = [
            {"center": pt(cx, cy), "seats": [pt(cx + dx, cy + dy) for dx, dy in HALL_SEATS], "spectators": box(cx + HALL_SPECTATORS[0], cy + HALL_SPECTATORS[1], *HALL_SPECTATORS[2:])}
            for cx, cy in HALL_TABLES
        ]
        d["$tables"] = "6 张牌桌，seats 依次是 0 左后、1 右后、2 左前；spectators 是观战区 [x, y, 宽, 高]。桌子多于 6 张时显示“还有 N 桌”。"
    else:
        d["seats"] = [pt(*s) for s in TABLE_SEATS]
        d["pile"] = pt(*TABLE_PILE)
        d["spectators"] = box(*TABLE_SPECTATORS)
        d["$seats"] = "seats 依次是 0 左、1 后、2 右；pile 是桌面中间出牌的位置；spectators 是观战区 [x, y, 宽, 高]。"
    return d


def final_overlay(name, out):
    """把头像圈按清单坐标叠到定稿图上，用来检查对齐。"""
    d = final_data(name)
    im = Image.open(FINAL[name]).convert("RGB")
    g = ImageDraw.Draw(im)
    r = d["avatarSize"] * W / 2
    dot = lambda x, y, color="#FFD166": g.ellipse([x * W - r, y * H - r, x * W + r, y * H + r], fill=color, outline="#333333", width=2)
    rect_ = lambda x, y, w, h: g.rectangle([x * W, y * H, (x + w) * W, (y + h) * H], outline="#2B7FFF", width=3)
    if name == "classroom":
        dot(*d["teacher"], color="#FF6B6B")
        for row in d["rows"]:
            (x1, y1), (x2, y2), n = row["from"], row["to"], row["seats"]
            for k in range(n):
                t = (k + 0.5) / n
                dot(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
    elif name == "club-hall":
        for t in d["tables"]:
            for s in t["seats"]:
                dot(*s)
            rect_(*t["spectators"])
    else:
        for s in d["seats"]:
            dot(*s)
        rect_(*d["spectators"])
        x, y = d["pile"]
        g.ellipse([x * W - 8, y * H - 8, x * W + 8, y * H + 8], outline="#2B7FFF", width=3)
    im.save(out)
    return out


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "i2i":  # i2i 场景 强度 种子...
        render_i2i(args[0], [int(x) for x in args[2:]] or [1, 2, 3], float(args[1]))
    elif cmd == "render":  # render 场景 种子...
        render(args[0], [int(x) for x in args[1:]] or [1, 2, 3])
    elif cmd == "sketch":
        for n in args or list(SCENES):
            print(sketch(n).relative_to(ROOT))
    else:
        {"diagram": diagram, "check": check}[cmd](args or list(SCENES))
