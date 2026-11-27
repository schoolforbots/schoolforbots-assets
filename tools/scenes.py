"""本机 ComfyUI 出图的公用函数，tools/campus_layout.py 和 tools/rooms_layout.py 共用。

- workflow()：Qwen-Image-Edit 按一张参考图（布局草图或已有插画）出图。
- refine_workflow()：Qwen-Image 图生图，在一张图上重画，denoise 越小越贴原图。
- comfy()：把工作流交给本机 ComfyUI（127.0.0.1:8188），等出图后返回 PNG 字节。

ComfyUI 建议这样启动，免得占满内存和显存：
  python_embeded/python.exe -s ComfyUI/main.py --windows-standalone-build --disable-auto-launch       --disable-pinned-memory --reserve-vram 4 --vram-headroom 3 --mmap-torch-files --cache-lru 1
"""
import json
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "http://127.0.0.1:8188"
W, H = 1664, 1040  # 出图尺寸，16:10，Qwen-Image 要 16 的倍数
COMFY_INPUT = Path(r"F:\Project\ComfyUI_windows_portable\ComfyUI\input")


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
