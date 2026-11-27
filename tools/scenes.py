"""室内场景（教室、社团大厅、牌桌）：几何位置只在这里定义一次，草图、插画和清单坐标都从它来。
校园全景图见 tools/campus_layout.py。这里的 comfy()、workflow()、refine_workflow() 两边共用。

  python tools/scenes.py sketch [场景...]    画布局草图 -> sources/layouts/<场景>.png
  python tools/scenes.py render [场景...]    用本机 ComfyUI 把草图渲染成插画 -> sources/raw/<场景>-<seed>.png
        --seed N   指定种子（默认 1）；--count N 连续出 N 张不同种子
  python tools/scenes.py refine 场景 文件 [--denoise=0.5]  在渲染结果上精修一遍（构图不变，补细节） -> sources/raw/
  python tools/scenes.py adopt 场景 文件    选定一张：校园进 campus/<--time=night|day>.webp，其它进 rooms/，坐标写进 manifest.json
  python tools/scenes.py overlay [场景...]   在选定的插画上叠坐标标记 -> sources/overlay/<场景>.png，用来检查对齐

所有坐标都是占图宽高的比例（0–1），原点在左上角。
"""
import json
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LAYOUTS = ROOT / "sources" / "layouts"
RAW = ROOT / "sources" / "raw"
OVERLAY = ROOT / "sources" / "overlay"
API = "http://127.0.0.1:8188"
COMFY_INPUT = Path(r"F:\Project\ComfyUI_windows_portable\ComfyUI\input")

W, H = 1664, 1040  # 16:10，Qwen-Image 要 16 的倍数

STYLE = (
    "细节丰富的等距扁平插画风格（像 Dribbble 上精致的扁平城市插画）：干净平整的色块和简洁的几何形状，"
    "但每个东西都画出很多小细节：窗框、窗台、遮阳棚、屋顶的瓦片和天台设备、门口的台阶和小招牌（招牌上不写字）、"
    "路边的行道树和灌木、长椅、路灯、花坛、自行车架、垃圾桶、小路的铺砖纹理。柔和的阴影，清新明亮的配色。"
    "画面里没有任何人物和动物，没有任何文字、字母和数字。"
)
KEEP = "严格保持草图的构图：每个色块的位置、大小和形状都不变，物体之间的相对位置完全不变，不添加草图里没有的大型建筑。"


def box(x, y, w, h):
    return {"x": x, "y": y, "w": w, "h": h}


# ---------------------------------------------------------------- 场景定义
# 每个场景：sketch 是草图里的色块，points/areas/rows 写进清单给前端用。

def classroom():
    rows = []
    for i in range(6):
        y = 0.44 + i * 0.095
        x1 = 0.17 - i * 0.022
        x2 = 0.83 + i * 0.022
        rows.append({"y": round(y, 4), "x1": round(x1, 4), "x2": round(x2, 4)})
    sketch = [
        ("rect", box(0, 0, 1, 1), "#E9D8B8"),  # 地板
        ("rect", box(0, 0, 1, 0.27), "#F3EBDD"),  # 前墙
        ("rect", box(0.27, 0.04, 0.46, 0.18), "#2F5D46"),  # 黑板
        ("rect", box(0.42, 0.27, 0.16, 0.06), "#8B5A2B"),  # 讲台
        ("rect", box(0.03, 0.06, 0.12, 0.16), "#A9D3F2"),  # 窗
        ("rect", box(0.85, 0.06, 0.12, 0.16), "#A9D3F2"),
    ]
    for r in rows:
        sketch.append(("rect", box(r["x1"], r["y"] + 0.012, r["x2"] - r["x1"], 0.035), "#A0703F"))  # 长课桌
    prompt = (
        "把这张色块草图画成一间明亮温馨的学校教室，从教室后方高处看向前方的黑板。"
        "上方深绿色是一块干净的大黑板（黑板上空白，不写字），黑板前棕色小块是老师的木制讲台，讲台后面留一块空地给老师站。"
        "左右两边浅蓝色是窗户，窗外是夜空和星星，教室里亮着温暖的灯。"
        "下面六条棕色横条是六排很长的木制连排课桌，一排比一排宽，课桌后面是连排长凳，桌上可以放几本书和文具，"
        "但课桌后面的位置是空的，等学生来坐。米色是木地板。"
    )
    teacher = {"x": 0.5, "y": 0.255}
    return {
        "sketch": sketch,
        "prompt": prompt,
        "manifest": {"teacher": [teacher["x"], teacher["y"]], "rows": rows, "rowsNote": "学生沿每排从 x1 到 x2 均匀排开，头像底边落在 y 上"},
    }


def _table_seats(cx, cy, rx, ry):
    """三个座位：0 左、1 上（远处）、2 右。"""
    return [[round(cx - rx * 1.25, 4), round(cy + ry * 0.1, 4)], [round(cx, 4), round(cy - ry * 1.35, 4)], [round(cx + rx * 1.25, 4), round(cy + ry * 0.1, 4)]]


def club_hall():
    tables = []
    sketch = [
        ("rect", box(0, 0, 1, 1), "#C99A6B"),  # 地板
        ("rect", box(0, 0, 1, 0.16), "#7A4B3A"),  # 后墙
        ("rect", box(0.38, 0.03, 0.24, 0.09), "#D9B44A"),  # 牌匾
    ]
    rx, ry = 0.075, 0.075 * W / H * 0.55
    for j, cy in enumerate([0.40, 0.76]):
        for i, cx in enumerate([0.19, 0.5, 0.81]):
            seats = _table_seats(cx, cy, rx, ry)
            tables.append({"center": [cx, cy], "seats": seats, "spectators": box(round(cx - 0.11, 4), round(cy + ry + 0.03, 4), 0.22, 0.06)})
            sketch.append(("ellipse", box(cx - rx, cy - ry, rx * 2, ry * 2), "#2E7D4F"))
            for sx, sy in seats:
                sketch.append(("rect", box(sx - 0.022, sy - 0.012, 0.044, 0.05), "#6B3E26"))
    prompt = (
        "把这张色块草图画成一间温馨的学校棋牌社团活动室，从高处斜着俯视。"
        "上方深棕色是后墙，墙上金色色块是一块空白的木牌匾（牌匾上不写字），墙边有书架、盆栽和挂灯。"
        "六个深绿色椭圆是六张铺着绿色绒布的椭圆形牌桌，两排三列，桌面上放着几叠扑克牌和筹码。"
        "每张桌子周围的三个深棕色小块是三把空着的木椅：左边一把、后面一把、右边一把。"
        "桌子前面留出空地。木地板，暖黄色的吊灯，夜晚的氛围。"
    )
    return {"sketch": sketch, "prompt": prompt, "manifest": {"tables": tables, "seatOrder": "0 左、1 后、2 右"}}


def club_table():
    cx, cy = 0.5, 0.55
    rx, ry = 0.24, 0.20
    seats = [[0.17, 0.50], [0.5, 0.2], [0.83, 0.50]]
    sketch = [
        ("rect", box(0, 0, 1, 1), "#C99A6B"),
        ("rect", box(0, 0, 1, 0.12), "#7A4B3A"),
        ("ellipse", box(cx - rx, cy - ry, rx * 2, ry * 2), "#2E7D4F"),
        ("rect", box(cx - 0.06, cy - 0.04, 0.12, 0.08), "#F2F2F2"),  # 桌面中间出牌处
    ]
    for sx, sy in seats:
        sketch.append(("rect", box(sx - 0.05, sy - 0.03, 0.10, 0.12), "#6B3E26"))
    sketch.append(("rect", box(0.12, 0.86, 0.76, 0.11), "#B5875A"))  # 观战区
    prompt = (
        "把这张色块草图画成学校棋牌社里一张斗地主牌桌的近景，从高处斜着俯视。"
        "中间深绿色大椭圆是一张铺绿色绒布的椭圆形牌桌，桌面正中间的白色块是一小叠摊开的扑克牌，桌边放着筹码。"
        "左、上、右三个深棕色块是三把空着的木椅，椅子上没有人。"
        "最下面浅棕色长条是给观众站的空地。上方深棕色是墙，挂着暖色的灯。木地板，温暖的夜晚氛围。"
    )
    return {
        "sketch": sketch,
        "prompt": prompt,
        "manifest": {"center": [cx, cy], "seats": seats, "seatOrder": "0 左、1 上、2 右", "spectators": box(0.12, 0.86, 0.76, 0.11)},
    }


DEFS = {"classroom": classroom, "club-hall": club_hall, "club-table": club_table}


# ---------------------------------------------------------------- 草图

def draw_sketch(name):
    d = DEFS[name]()
    img = Image.new("RGB", (W, H), "white")
    g = ImageDraw.Draw(img)
    for kind, b, color in d["sketch"]:
        xy = [b["x"] * W, b["y"] * H, (b["x"] + b["w"]) * W, (b["y"] + b["h"]) * H]
        (g.ellipse if kind == "ellipse" else g.rectangle)(xy, fill=color)
    LAYOUTS.mkdir(parents=True, exist_ok=True)
    out = LAYOUTS / f"{name}.png"
    img.save(out)
    print("sketch", out.relative_to(ROOT))
    return out


# ---------------------------------------------------------------- ComfyUI

def post(path, payload):
    req = urllib.request.Request(API + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def workflow(image, prompt, seed):
    enc = lambda text: {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "prompt": text, "vae": ["3", 0], "image1": ["4", 0]}}
    ref = lambda c: {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": [c, 0], "reference_latents_method": "index_timestep_zero"}}
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_fp8_e4m3fn_scaled_lightning_comfyui_4steps_v1.0.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": image}},
        "5": enc(prompt),
        "6": enc(""),
        "7": ref("5"),
        "8": ref("6"),
        "9": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "10": {"class_type": "CFGNorm", "inputs": {"model": ["9", 0], "strength": 1.0}},
        "11": {"class_type": "EmptySD3LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "12": {"class_type": "KSampler", "inputs": {
            "model": ["10", 0], "positive": ["7", 0], "negative": ["8", 0], "latent_image": ["11", 0],
            "seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": "sfb_scene"}},
    }


def refine_workflow(image, prompt, seed, denoise):
    """用 Qwen-Image 文生图模型在渲染结果上重画一遍（图生图），构图不变、补细节和质感。"""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "4": {"class_type": "LoadImage", "inputs": {"image": image}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": "人物, 文字, 水印, 模糊, 低质量, 扭曲"}},
        "7": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["3", 0]}},
        "9": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "12": {"class_type": "KSampler", "inputs": {
            "model": ["9", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0],
            "seed": seed, "steps": 24, "cfg": 3.0, "sampler_name": "euler", "scheduler": "simple", "denoise": denoise}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["3", 0]}},
        "14": {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": "sfb_scene_refine"}},
    }


def refine(name, file, seed, denoise):
    src = Path(file)
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    image_name = f"sfb_refine_{src.stem}.png"
    (COMFY_INPUT / image_name).write_bytes(src.read_bytes())
    d = DEFS[name]()
    out = RAW / f"{src.stem}-r{int(denoise * 100)}-{seed}.png"
    out.write_bytes(comfy(image_name, d["prompt"] + STYLE, seed, refine_workflow(image_name, d["prompt"] + STYLE, seed, denoise)))
    print("refine", out.relative_to(ROOT), flush=True)


def comfy(image_name, prompt, seed, graph=None):
    graph = graph or workflow(image_name, prompt, seed)
    pid = post("/prompt", {"prompt": graph, "client_id": str(uuid.uuid4())})["prompt_id"]
    while True:
        hist = json.load(urllib.request.urlopen(f"{API}/history/{pid}"))
        if pid in hist:
            if hist[pid].get("status", {}).get("status_str") == "error":
                raise RuntimeError(json.dumps(hist[pid]["status"], ensure_ascii=False)[:1500])
            if hist[pid].get("outputs"):
                img = hist[pid]["outputs"]["14"]["images"][0]
                break
        time.sleep(1)
    q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img["subfolder"], "type": img["type"]})
    return urllib.request.urlopen(f"{API}/view?{q}").read()


def render(name, seed):
    sketch = draw_sketch(name)
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    image_name = f"sfb_layout_{name}.png"
    (COMFY_INPUT / image_name).write_bytes(sketch.read_bytes())
    d = DEFS[name]()
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"{name}-{seed}.png"
    out.write_bytes(comfy(image_name, d["prompt"] + KEEP + STYLE, seed))
    print("render", out.relative_to(ROOT), flush=True)


# ---------------------------------------------------------------- 选定、写清单、检查

def arrays(v):
    """清单里的矩形写成 [x, y, 宽, 高]。"""
    if isinstance(v, dict) and set(v) == {"x", "y", "w", "h"}:
        return [round(v[k], 4) for k in ("x", "y", "w", "h")]
    if isinstance(v, dict):
        return {k: arrays(x) for k, x in v.items()}
    if isinstance(v, list):
        return [arrays(x) for x in v]
    return v


HOURS = {"night": "18:00-06:00", "day": "06:00-18:00"}


def adopt(name, file, time="night"):
    """选定插画：转 WebP，坐标写进清单。校园分白天、夜晚两张，放 campus/；其它场景放 rooms/。"""
    im = Image.open(file).convert("RGB")
    if im.size != (W, H):
        raise SystemExit(f"{file} 是 {im.size}，要 {(W, H)}")
    rel = f"campus/{time}.webp" if name == "campus" else f"rooms/{name}.webp"
    (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ROOT / rel, "WEBP", quality=82, method=6)
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf8"))
    data = arrays(DEFS[name]()["manifest"])
    if name == "campus":
        old = manifest.get("campus", {})
        scenes = {k: v for k, v in old.get("scenes", {}).items() if v}
        scenes[time] = {"image": rel, "hours": HOURS[time]}
        manifest["campus"] = {
            "width": W,
            "height": H,
            "scenes": {k: scenes.get(k) for k in ("night", "day")},
            "$coords": old.get("$coords"),
            **data,
        }
    else:
        rooms = manifest.setdefault("rooms", {})
        rooms[name] = {"image": rel, "width": W, "height": H, **data}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print("adopt", rel, f"{(ROOT / rel).stat().st_size // 1024} KB")


def overlay(name, time="night"):
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf8"))
    m = manifest["campus"] if name == "campus" else manifest["rooms"][name]
    image = m["scenes"][time]["image"] if name == "campus" else m["image"]
    im = Image.open(ROOT / image).convert("RGB")
    g = ImageDraw.Draw(im)

    def rect(b, color):
        if b:
            x, y, w, h = b
            g.rectangle([x * W, y * H, (x + w) * W, (y + h) * H], outline=color, width=4)

    def dot(p, color, r=22):
        g.ellipse([p[0] * W - r, p[1] * H - r, p[0] * W + r, p[1] * H + r], outline=color, width=5)

    for loc in m.get("locations", {}).values():
        rect(loc["area"], "#00E5FF")
        dot(loc["labelAt"], "#FF3B30", 12)
    if "teacher" in m:
        dot(m["teacher"], "#FF3B30")
    for r in m.get("rows", []):
        g.line([r["x1"] * W, r["y"] * H, r["x2"] * W, r["y"] * H], fill="#00E5FF", width=4)
    for t in m.get("tables", []):
        for s in t["seats"]:
            dot(s, "#FF3B30")
        rect(t["spectators"], "#00E5FF")
    for s in m.get("seats", []):
        dot(s, "#FF3B30", 40)
    rect(m.get("spectators"), "#00E5FF")
    OVERLAY.mkdir(parents=True, exist_ok=True)
    out = OVERLAY / f"{name}{'-' + time if name == 'campus' else ''}.png"
    im.save(out)
    print("overlay", out.relative_to(ROOT))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = {a.split("=")[0]: (a.split("=") + [""])[1] for a in sys.argv[1:] if a.startswith("--")}
    cmd, names = args[0], args[1:]
    if cmd == "adopt":
        return adopt(names[0], names[1], opt.get("--time") or "night")
    if cmd == "refine":
        return refine(names[0], names[1], int(opt.get("--seed") or 1), float(opt.get("--denoise") or 0.5))
    names = names or list(DEFS)
    if cmd == "sketch":
        for n in names:
            draw_sketch(n)
    elif cmd == "render":
        seed, count = int(opt.get("--seed") or 1), int(opt.get("--count") or 1)
        for n in names:
            for s in range(seed, seed + count):
                render(n, s)
    elif cmd == "overlay":
        for n in names:
            overlay(n, opt.get("--time") or "night")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
