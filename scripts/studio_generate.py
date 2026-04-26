#!/usr/bin/env python3
import argparse
import base64
import json
import math
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image


GRSAI_BASE = "https://grsaiapi.com"
GRSAI_DOMESTIC_BASE = "https://grsai.dakka.com.cn"

BANANA_4K_SIZES: Dict[str, Tuple[int, int]] = {
    "auto": (5632, 3072),
    "1:1": (4096, 4096),
    "2:3": (3392, 5056),
    "3:2": (5056, 3392),
    "3:4": (3584, 4800),
    "4:3": (4800, 3584),
    "4:1": (8256, 2048),
    "1:4": (2048, 8256),
    "4:5": (3712, 4608),
    "5:4": (4608, 3712),
    "8:1": (11712, 1408),
    "1:8": (1408, 11712),
    "9:16": (3072, 5504),
    "16:9": (5504, 3072),
    "9:21": (2688, 6336),
    "21:9": (6336, 2688),
}

DEVICE_CONFIGS: Dict[str, Tuple[str, int, int]] = {
    "iphone_6_5_inch": ('iPhone AppStore 上架图 (6.5")', 1242, 2688),
    "ipad_pro_12_9": ('iPad Pro 12.9" AppStore 上架图', 2048, 2732),
    "ipad_pro_11": ('iPad Pro 11" AppStore 上架图', 1668, 2388),
    "apple_app_icon": ("App Store 图标 (Icon)", 1024, 1024),
    "google_play_icon": ("Google Play 图标 (Icon)", 512, 512),
    "google_play_feature": ("Google Play 背景图 (Feature Graphic)", 1024, 500),
    "steam_header": ("Steam 顶部页头 (Header Capsule)", 460, 215),
    "steam_main": ("Steam 商店胶囊 (Main Capsule)", 616, 353),
    "chrome_promo": ("Chrome 商店宣传 (Web Store Promo)", 440, 280),
}

GENERAL_RATIOS: Dict[str, Tuple[int, int]] = {
    "1:1": (4096, 4096),
    "4:5": (3712, 4608),
    "5:4": (4608, 3712),
    "2:3": (3392, 5056),
    "3:2": (5056, 3392),
    "3:4": (3584, 4800),
    "4:3": (4800, 3584),
    "9:16": (3072, 5504),
    "16:9": (5504, 3072),
    "9:21": (2688, 6336),
    "21:9": (6336, 2688),
    "1:4": (2048, 8256),
    "4:1": (8256, 2048),
    "1:8": (1408, 11712),
    "8:1": (11712, 1408),
}

MARKETING_TEMPLATES: Dict[str, Tuple[str, int, int]] = {
    "youtube_banner": ("YouTube 频道封面 (Art)", 2560, 1440),
    "og_image": ("社交媒体卡片 (OG Image)", 1200, 630),
    "ig_story": ("IG Story 故事 / Shorts", 1080, 1920),
    "webtoon": ("漫画长条图 (Webtoon Strip)", 800, 3200),
    "ig_carousel_2": ("连贯轮播-2张 (Carousel)", 2160, 1080),
    "ig_carousel_4": ("连贯轮播-4张 (Carousel)", 4320, 1080),
}

PORTRAIT_TEMPLATES: Dict[str, Tuple[str, int, int]] = {
    "business_headshot": ("商务形象照 (Business Headshot)", 1024, 1280),
    "glamour_portrait": ("时尚艺术照 (Glamour Portrait)", 1024, 1536),
    "passport_photo": ("证件照 (ID / Passport Photo)", 600, 600),
}

COMMERCIAL_TEMPLATES: Dict[str, Tuple[str, int, int]] = {
    "product_poster": ("产品海报 (Product Poster)", 1080, 1350),
    "luxury_showcase": ("奢侈品展柜 (Luxury Showcase)", 2160, 1080),
    "ecommerce_main": ("电商主图 (E-commerce Main)", 1024, 1024),
}


def parse_grid(grid: str) -> Tuple[int, int, int, str]:
    if not grid:
        grid = "1x1"
    if grid.isdigit():
        n = max(1, int(grid))
        return n, n, n * n, f"{n}x{n}"
    parts = grid.lower().split("x")
    rows = int(parts[0]) if parts and parts[0].isdigit() else 1
    cols = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else rows
    rows = max(1, rows)
    cols = max(1, cols)
    return rows, cols, rows * cols, f"{rows}x{cols}"


def is_allowed_output_grid(rows: int, cols: int) -> bool:
    total = rows * cols
    return total == 1 or total % 2 == 0 or rows == cols


def closest_aspect_ratio(width: int, height: int) -> str:
    supported = [
        ("1:1", 1.0),
        ("16:9", 16 / 9),
        ("9:16", 9 / 16),
        ("4:3", 4 / 3),
        ("3:4", 3 / 4),
        ("3:2", 3 / 2),
        ("2:3", 2 / 3),
        ("5:4", 5 / 4),
        ("4:5", 4 / 5),
        ("21:9", 21 / 9),
        ("9:19.5", 9 / 19.5),
        ("9:19", 9 / 19),
        ("3:5", 3 / 5),
    ]
    ratio = width / height
    return min(supported, key=lambda item: abs(ratio - item[1]))[0]


def tiered_dimensions(width: int, height: int, tier: str) -> Tuple[int, int]:
    tier = tier.upper()
    if tier == "4K":
        target_ratio = width / height
        key = min(BANANA_4K_SIZES, key=lambda k: abs((BANANA_4K_SIZES[k][0] / BANANA_4K_SIZES[k][1]) - target_ratio))
        return BANANA_4K_SIZES[key]
    max_side = 2048 if tier == "2K" else 1024
    scale = max_side / max(width, height)
    return round(width * scale), round(height * scale)


def cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    resized = img.convert("RGB").resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def split_grid(img: Image.Image, rows: int, cols: int, target_w: int, target_h: int) -> List[Image.Image]:
    width, height = img.size
    pieces: List[Image.Image] = []
    for r in range(rows):
        for c in range(cols):
            left = math.floor(c * width / cols)
            top = math.floor(r * height / rows)
            right = math.floor((c + 1) * width / cols)
            bottom = math.floor((r + 1) * height / rows)
            piece = img.crop((left, top, right, bottom))
            pieces.append(cover_resize(piece, target_w, target_h))
    return pieces


def hidden_guardrail() -> str:
    return (
        "Treat every instruction as hidden production guidance only. Do not render any percentages, "
        "measurements, aspect-ratio notation, layout guides, crop marks, arrows, labels, callouts, "
        "watermarks, debug overlays, or prompt fragments in the final image unless the user explicitly "
        "asks for that text as part of the app UI."
    )


def layout_instruction(mode: str, width: int, height: int, template_id: Optional[str]) -> str:
    if template_id == "youtube_banner":
        return (
            "CRITICAL LAYOUT RULE: Create a YouTube Channel Banner composition. Keep all critical "
            "visual elements in the exact center safe area. Outer edges should only contain continuous "
            "background scenery, patterns, or textures. Never draw safe-area boxes or layout guides."
        )
    if template_id == "og_image":
        return (
            "CRITICAL LAYOUT RULE: Create a Social Media Link Preview image. Keep the main subject "
            "centered with generous safe margins so platform crops do not remove key details."
        )
    if template_id == "ig_story":
        return (
            "CRITICAL LAYOUT RULE: Create a vertical social media Story. Avoid placing critical subjects "
            "near the top profile/header UI zone or bottom caption/interactions zone."
        )
    if template_id and template_id.startswith("ig_carousel_"):
        slides = template_id.split("_")[-1]
        return (
            f"CRITICAL LAYOUT RULE: Create a continuous seamless panorama spanning {slides} square frames. "
            "Do not draw vertical dividing lines, borders, or grid gaps. Ensure the image flows naturally left to right."
        )
    if template_id == "webtoon":
        return (
            "CRITICAL LAYOUT RULE: Create a continuous vertical comic/webtoon strip with 3 or 4 scenes "
            "flowing top to bottom. Do not draw literal panel guides unless requested."
        )
    is_appstore = mode == "appstore"
    is_phone = width < height and width / height < 0.6
    if is_phone:
        status = (
            "Render a realistic minimalist iPhone status bar at the very top."
            if is_appstore
            else "Do not render phone status bars, home indicators, notches, or hardware frames."
        )
        return (
            "CRITICAL LAYOUT RULE: Create a centered composition. Keep important visual focal points "
            f"inside the central safe area. {status} Never draw layout guides, measurements, vignettes, or borders."
        )
    status = (
        "Render a realistic iPadOS status bar at the top when appropriate."
        if is_appstore
        else "Do not render device status bars, bezels, or operating system interface elements."
    )
    return (
        f"LAYOUT RULE: Create a balanced high-fidelity composition. Keep primary subjects away from margins. {status} "
        "Never draw guides, measurements, shadows, vignettes, or borders around the edges."
    )


def build_prompt(
    *,
    mode: str,
    prompt: str,
    width: int,
    height: int,
    image_size: Optional[str],
    batch: bool,
    rows: int,
    cols: int,
    template_id: Optional[str],
    device_name: Optional[str],
    has_refs: bool,
) -> str:
    layout = layout_instruction(mode, width, height, template_id)
    reference_hint = (
        "Use the provided reference image as a strong visual guide for composition, subject identity, style, and color palette. "
        "Keep key reference characteristics clearly recognizable in the generated result."
        if has_refs
        else ""
    )
    if batch:
        total = rows * cols
        h_lines = rows - 1
        v_lines = cols - 1
        appstore_lines = ""
        if mode == "appstore":
            appstore_lines = (
                f"2. Each cell represents a FULL {device_name or 'device'} graphic.\n"
                "3. If the graphic represents a mobile or tablet screen, each cell MUST have its OWN Status Bar at the very top."
            )
        sections = [
            f"Create a high-resolution {rows}x{cols} GRID containing EXACTLY {total} DISTINCT variations.",
            "Follow every instruction below internally only. None of these instructions may appear as visible text or annotations in the image.",
            hidden_guardrail(),
            f"Total image resolution is {image_size or '4K'}.",
            "CRITICAL STRUCTURE & GRID LAYOUT (MUST FOLLOW EXACTLY):",
            f"- The final canvas MUST contain EXACTLY {total} cells: {rows} rows x {cols} columns. Count the cells before rendering.",
            f"- The image MUST be strictly divided into EXACTLY {rows} rows and {cols} columns ({total} equal grid cells).",
            f"- You MUST draw EXACTLY {h_lines} horizontal dividing line(s) and EXACTLY {v_lines} vertical dividing line(s) to form the grid.",
            f"- Do NOT hallucinate or change the grid size. You MUST yield exactly {total} images. Do NOT draw any grid except {rows}x{cols}.",
            f"- Do NOT add any extra image, bonus panel, cover image, title card, header, footer, inset preview, decorative thumbnail, or partial extra cell outside those {total} cells.",
            "- Every cell must occupy one grid slot only. No merged cells, no overlapping cells, no partial extra cells.",
            "- NO GAPS, NO WHITE SPACE between grid cells. The cells must touch each other seamlessly.",
            f"FOR EACH GRID CELL (Must apply to ALL {total} images individually):",
            "1. Each cell represents a SEPARATE, COMPLETE artwork representing the brief.",
            appstore_lines,
            f"Instruction for EACH cell: {layout}",
            f"GLOBAL CREATIVE BRIEF: {prompt}",
            f"REMINDER: You are generating {total} SEPARATE, COMPLETE images tiled together. Do not treat the full canvas as one big single subject image.",
        ]
        if reference_hint:
            sections.append(reference_hint)
        return "\n".join([s for s in sections if s])
    orientation = "landscape" if width / height > 1.05 else "portrait" if width / height < 0.95 else "square"
    sections = [
        f"Production context: {device_name or template_id or mode}.",
        f"Creative brief:\n{prompt}",
        f"Target canvas guidance: compose for a {width}x{height}px {orientation} canvas"
        f"{', ' + image_size + ' export tier' if image_size else ''}. Use these dimensions only for composition, framing, and aspect ratio. Do not render the numbers or any guides as visible text.",
        hidden_guardrail(),
        "Ensure professional, clean, modern presentation and high-fidelity rendering.",
        f"Layout Instructions (CRITICAL):\n{layout}",
    ]
    if reference_hint:
        sections.append(reference_hint)
    if mode == "general":
        return "\n\n".join(sections[1:-1] + ([reference_hint] if reference_hint else []))
    return "\n\n".join(sections)


def reference_to_url(value: str) -> str:
    if re.match(r"^https?://", value, re.I) or value.startswith("data:"):
        return value
    path = Path(value).expanduser()
    if not path.exists():
        return value
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def http_json(url: str, body: Dict[str, Any], api_key: str, timeout: int = 60) -> Dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {err}") from exc
    if text.strip().startswith("data:"):
        text = text.strip().replace("data:", "", 1).splitlines()[0].strip()
    return json.loads(text)


def clean_base_url(value: str) -> str:
    return value.rstrip("/")


def configured_base_url(args: argparse.Namespace, *, domestic: bool = False) -> str:
    if domestic:
        value = args.domestic_base_url or os.environ.get("GRSAI_DOMESTIC_BASE_URL") or GRSAI_DOMESTIC_BASE
    else:
        value = args.base_url or os.environ.get("GRSAI_BASE_URL") or GRSAI_BASE
    return clean_base_url(value)


def configured_draw_url(args: argparse.Namespace, model: str, domestic: bool) -> str:
    is_gpt_image2 = model == "gpt-image-2"
    if is_gpt_image2:
        override = args.gpt_image2_draw_url or args.draw_url or os.environ.get("GRSAI_GPT_IMAGE2_DRAW_URL") or os.environ.get("GRSAI_DRAW_URL")
        return override or f"{configured_base_url(args)}/v1/draw/completions"

    override = args.draw_url or os.environ.get("GRSAI_DRAW_URL")
    if override:
        return override
    return f"{configured_base_url(args, domestic=domestic)}/v1/draw/nano-banana"


def configured_result_url(args: argparse.Namespace, domestic: bool) -> str:
    override = args.result_url or os.environ.get("GRSAI_RESULT_URL")
    if override:
        return override
    return f"{configured_base_url(args, domestic=domestic)}/v1/draw/result"


def extract_image_urls(data: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    for item in data.get("results") or []:
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    for item in data.get("images") or []:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    if data.get("image_url"):
        urls.append(data["image_url"])
    return urls


def poll_grsai(api_key: str, task_id: str, result_url: str, attempts: int, interval: float) -> str:
    for attempt in range(attempts):
        time.sleep(2 if attempt == 0 else interval)
        data = http_json(result_url, {"id": task_id}, api_key, timeout=30)
        if data.get("code") == -22:
            continue
        if "data" in data and isinstance(data["data"], dict):
            task = data["data"]
        else:
            task = data
        if data.get("code") not in (None, 0, -22):
            raise RuntimeError(f"Polling failed: {data.get('msg') or data}")
        status = task.get("status")
        if status == "succeeded":
            urls = extract_image_urls(task)
            if urls:
                return urls[0]
            raise RuntimeError("Task succeeded but no image URL was found")
        if status == "failed":
            raise RuntimeError(f"Generation failed: {task.get('failure_reason') or task.get('error') or task}")
    raise TimeoutError("Generation polling timed out")


def load_image(source: str) -> Image.Image:
    if source.startswith("data:"):
        payload = source.split(",", 1)[1]
        return Image.open(BytesIO(base64.b64decode(payload))).convert("RGB")
    if re.match(r"^https?://", source, re.I):
        with urllib.request.urlopen(source, timeout=120) as resp:
            return Image.open(BytesIO(resp.read())).convert("RGB")
    return Image.open(Path(source).expanduser()).convert("RGB")


def save_images(images: List[Image.Image], out_dir: Path, prefix: str) -> List[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[str] = []
    for i, img in enumerate(images, start=1):
        suffix = f"_{i:02d}" if len(images) > 1 else ""
        path = out_dir / f"{prefix}{suffix}.png"
        img.save(path, format="PNG")
        paths.append(str(path))
    return paths


def resolve_base_format(args: argparse.Namespace) -> Tuple[str, int, int, Optional[str]]:
    if args.mode == "appstore":
        name, width, height = DEVICE_CONFIGS[args.device]
        return name, width, height, None
    if args.mode == "general":
        width, height = GENERAL_RATIOS[args.ratio]
        return args.ratio, width, height, None
    templates: Dict[str, Tuple[str, int, int]]
    if args.mode == "marketing":
        templates = MARKETING_TEMPLATES
    elif args.mode == "portrait":
        templates = PORTRAIT_TEMPLATES
    else:
        templates = COMMERCIAL_TEMPLATES
    name, width, height = templates[args.template]
    return name, width, height, args.template


def make_plan(args: argparse.Namespace) -> Dict[str, Any]:
    selected_model = args.model.strip()
    is_gpt_image2 = selected_model == "gpt-image-2"
    rows, cols, total, grid_label = parse_grid(args.grid)
    batch = args.count != 1 or grid_label != "1x1"
    if args.count and args.count > 1 and grid_label == "1x1":
        raise ValueError("--count > 1 requires --grid, for example --grid 2x3")
    if batch and not is_allowed_output_grid(rows, cols):
        raise ValueError(f"Grid {grid_label} is not allowed. Use 1, an even total, or a square grid.")
    if is_gpt_image2:
        batch = False
        rows, cols, total, grid_label = 1, 1, 1, "1x1"
    if args.size.upper() == "4K" and batch and args.mode != "appstore":
        raise ValueError("4K multi-output batches are disabled. Use 1K/2K or a single 4K output.")

    device_name, base_w, base_h, template_id = resolve_base_format(args)
    canvas_w, canvas_h = tiered_dimensions(base_w, base_h, args.size)
    target_w, target_h = canvas_w, canvas_h
    canvas_size = args.size.upper()

    if batch:
        grid_w = canvas_w * cols
        grid_h = canvas_h * rows
        canvas_w, canvas_h = tiered_dimensions(grid_w, grid_h, "4K")
        canvas_size = "4K"

    urls = [reference_to_url(v) for v in args.reference]
    prompt = build_prompt(
        mode=args.mode,
        prompt=args.prompt,
        width=base_w if args.mode == "appstore" else canvas_w,
        height=base_h if args.mode == "appstore" else canvas_h,
        image_size=canvas_size,
        batch=batch,
        rows=rows,
        cols=cols,
        template_id=template_id,
        device_name=device_name,
        has_refs=bool(urls),
    )

    if is_gpt_image2:
        draw_url = configured_draw_url(args, selected_model, domestic=False)
        request_body = {
            "size": "auto",
            "prompt": prompt,
            "urls": urls,
            "badPrompt": "",
            "model": selected_model,
            "webHook": "",
            "shutProgress": False,
            "variants": 1,
            "cdn": "",
        }
        poll_domestic = False
    else:
        draw_url = configured_draw_url(args, selected_model, domestic=bool(args.domestic))
        request_body = {
            "model": selected_model,
            "prompt": prompt,
            "aspectRatio": closest_aspect_ratio(canvas_w, canvas_h),
            "webHook": "-1",
            "shutProgress": False,
            "urls": urls,
            "imageSize": canvas_size,
        }
        poll_domestic = bool(args.domestic)
    result_url = configured_result_url(args, domestic=poll_domestic)

    return {
        "model": selected_model,
        "mode": args.mode,
        "batch": batch,
        "rows": rows,
        "cols": cols,
        "total": total,
        "grid": grid_label,
        "base": {"name": device_name, "width": base_w, "height": base_h},
        "provider_canvas": {"width": canvas_w, "height": canvas_h, "imageSize": None if is_gpt_image2 else canvas_size},
        "target_output": {"width": target_w if batch or args.mode != "appstore" else base_w, "height": target_h if batch or args.mode != "appstore" else base_h},
        "draw_url": draw_url,
        "result_url": result_url,
        "poll_domestic": poll_domestic,
        "request_body": request_body,
    }


def submit_and_process(args: argparse.Namespace, plan: Dict[str, Any]) -> Dict[str, Any]:
    api_key = args.api_key or os.environ.get("GRSAI_API_KEY") or ""
    if not api_key:
        raise RuntimeError("Missing API key. Pass --api-key or set GRSAI_API_KEY.")
    task_data = http_json(plan["draw_url"], plan["request_body"], api_key, timeout=args.submit_timeout)
    urls = extract_image_urls(task_data)
    if urls:
        image_url = urls[0]
    elif task_data.get("id"):
        image_url = poll_grsai(api_key, task_data["id"], plan["result_url"], args.poll_attempts, args.poll_interval)
    elif isinstance(task_data.get("data"), dict) and task_data["data"].get("id"):
        image_url = poll_grsai(api_key, task_data["data"]["id"], plan["result_url"], args.poll_attempts, args.poll_interval)
    else:
        raise RuntimeError(f"Task submission failed: {task_data}")

    original = load_image(image_url)
    out_dir = Path(args.out).expanduser()
    raw_path = None
    if args.save_raw:
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = out_dir / f"{args.prefix}_raw.png"
        original.save(raw_path, format="PNG")

    target_w = int(plan["target_output"]["width"])
    target_h = int(plan["target_output"]["height"])
    if plan["batch"]:
        finals = split_grid(original, int(plan["rows"]), int(plan["cols"]), target_w, target_h)
    else:
        finals = [cover_resize(original, target_w, target_h)]
    paths = save_images(finals, out_dir, args.prefix)
    return {
        "success": True,
        "image_url": image_url,
        "raw_path": str(raw_path) if raw_path else None,
        "outputs": paths,
        "count": len(paths),
        "plan": {k: v for k, v in plan.items() if k != "request_body"},
    }


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone Screenshot Studio Pro generator for agents.")
    parser.add_argument("--prompt", required=True, help="Creative brief.")
    parser.add_argument("--model", default="nano-banana", help="Grsai model, e.g. nano-banana or gpt-image-2.")
    parser.add_argument("--mode", choices=["appstore", "general", "marketing", "portrait", "commercial"], default="general")
    parser.add_argument("--device", choices=sorted(DEVICE_CONFIGS), default="iphone_6_5_inch")
    parser.add_argument("--ratio", choices=sorted(GENERAL_RATIOS), default="1:1")
    parser.add_argument("--template", help="Template id for marketing/portrait/commercial modes.")
    parser.add_argument("--size", choices=["1K", "2K", "4K", "1k", "2k", "4k"], default="2K")
    parser.add_argument("--grid", default="1x1", help="Grid such as 2x3, 3x3, 5x5.")
    parser.add_argument("--count", type=int, default=1, help="Expected output count; --grid controls actual layout.")
    parser.add_argument("--reference", action="append", default=[], help="Reference image URL, data URL, or local file. Repeatable.")
    parser.add_argument("--api-key", default="", help="Grsai API key. Defaults to GRSAI_API_KEY env var.")
    parser.add_argument("--base-url", default="", help="Custom Grsai base URL. Defaults to GRSAI_BASE_URL or https://grsaiapi.com.")
    parser.add_argument("--domestic-base-url", default="", help="Custom domestic base URL. Defaults to GRSAI_DOMESTIC_BASE_URL.")
    parser.add_argument("--draw-url", default="", help="Full custom draw endpoint. Overrides --base-url for Banana models.")
    parser.add_argument("--gpt-image2-draw-url", default="", help="Full custom GPT Image2 draw endpoint. Defaults to <base-url>/v1/draw/completions.")
    parser.add_argument("--result-url", default="", help="Full custom polling endpoint. Defaults to <base-url>/v1/draw/result.")
    parser.add_argument("--domestic", action="store_true", help="Use domestic Grsai endpoint for Banana models.")
    parser.add_argument("--out", default="./outputs", help="Output directory.")
    parser.add_argument("--prefix", default="studio", help="Output filename prefix.")
    parser.add_argument("--save-raw", action="store_true", help="Save provider raw image before post-processing.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and request body without network calls.")
    parser.add_argument("--submit-timeout", type=int, default=600)
    parser.add_argument("--poll-attempts", type=int, default=300)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    args = parser.parse_args()

    if args.mode == "marketing" and not args.template:
        args.template = "youtube_banner"
    if args.mode == "portrait" and not args.template:
        args.template = "business_headshot"
    if args.mode == "commercial" and not args.template:
        args.template = "product_poster"
    if args.template:
        allowed = {
            "marketing": MARKETING_TEMPLATES,
            "portrait": PORTRAIT_TEMPLATES,
            "commercial": COMMERCIAL_TEMPLATES,
        }.get(args.mode)
        if allowed is not None and args.template not in allowed:
            raise SystemExit(f"Unknown template {args.template!r} for mode {args.mode}.")

    try:
        plan = make_plan(args)
        if args.dry_run:
            print_json({"success": True, "dry_run": True, "plan": plan})
            return 0
        result = submit_and_process(args, plan)
        print_json(result)
        return 0
    except Exception as exc:
        print_json({"success": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
