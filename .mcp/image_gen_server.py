#!/usr/bin/env python3
"""
Image Generation MCP Server — Playwright Text Adventure Game
============================================================
通过 MCP 协议将 AI 图像生成能力暴露给 GitHub Copilot。

切换提供商：修改 .vscode/mcp.json 中的 API_PROVIDER 和 API_KEY 即可。
支持：placeholder（测试用）| siliconflow | openai | stability
"""
import asyncio
import io
import json
import os
import sys
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── 配置（从环境变量读取）─────────────────────────────────────────────────────────
API_PROVIDER = os.getenv("API_PROVIDER", "placeholder")   # placeholder | siliconflow | openai | stability
API_KEY      = os.getenv("API_KEY", "")
SF_MODEL     = os.getenv("SF_MODEL", "black-forest-labs/FLUX.1-schnell")
OUTPUT_DIR   = os.getenv(
    "OUTPUT_DIR",
    str(Path(__file__).parent.parent / "docs" / "scenes")
)

# ── MCP Server 实例 ────────────────────────────────────────────────────────────
server = Server("playwright-image-gen")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="generate_image",
            description=(
                "为 Playwright 文字冒险游戏生成场景背景图片，并保存到 docs/scenes/ 目录。\n"
                f"当前提供商：{API_PROVIDER}（在 .vscode/mcp.json 中切换）"
            ),
            inputSchema={
                "type": "object",
                "required": ["prompt", "filename"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "英文图像描述 prompt。"
                            "例如：'dark mysterious forest at night, fog, moonlight, cinematic, fantasy art'"
                        ),
                    },
                    "filename": {
                        "type": "string",
                        "description": "保存的文件名（不含路径），例如：'forest_night.png'",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "负向提示词，描述不想出现的内容",
                        "default": "text, watermark, signature, blurry, low quality, ugly",
                    },
                    "width": {
                        "type": "integer",
                        "description": "图片宽度（像素），默认 1280",
                        "default": 1280,
                    },
                    "height": {
                        "type": "integer",
                        "description": "图片高度（像素），默认 720",
                        "default": 720,
                    },
                },
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "generate_image":
        raise ValueError(f"未知工具: {name}")

    prompt          = arguments["prompt"]
    filename        = arguments["filename"]
    negative_prompt = arguments.get("negative_prompt", "text, watermark, blurry, low quality, ugly")
    width           = int(arguments.get("width", 1280))
    height          = int(arguments.get("height", 720))

    # 确保输出目录存在
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    try:
        img_bytes = await _generate(prompt, negative_prompt, width, height)
        out_path.write_bytes(img_bytes)
        result = {
            "success":  True,
            "path":     str(out_path),
            "provider": API_PROVIDER,
            "prompt":   prompt,
            "size":     f"{width}x{height}",
        }
    except Exception as exc:
        result = {"success": False, "error": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# ── 路由到各提供商 ─────────────────────────────────────────────────────────────

async def _generate(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    match API_PROVIDER:
        case "placeholder":
            return _placeholder(prompt, width, height)
        case "siliconflow":
            return await _siliconflow(prompt, negative_prompt, width, height)
        case "openai":
            return await _openai_dalle(prompt, width, height)
        case "stability":
            return await _stability(prompt, negative_prompt, width, height)
        case _:
            raise ValueError(
                f"未知提供商 '{API_PROVIDER}'，"
                "在 .vscode/mcp.json 中将 API_PROVIDER 设为: placeholder | siliconflow | openai | stability"
            )


# ── 占位符（用 PIL 生成渐变图，无需 API Key）──────────────────────────────────

def _placeholder(prompt: str, width: int, height: int) -> bytes:
    """根据 prompt 哈希生成带标注的渐变测试图。"""
    from PIL import Image, ImageDraw, ImageFont
    import hashlib

    h = hashlib.md5(prompt.encode()).hexdigest()
    r1 = int(h[0:2], 16) // 5
    g1 = int(h[2:4], 16) // 5
    b1 = int(h[4:6], 16) // 4 + 20
    r2 = int(h[6:8], 16) // 3
    g2 = int(h[8:10], 16) // 3
    b2 = int(h[10:12], 16) // 3 + 60

    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for x in range(width):
        t = x / width
        draw.line([(x, 0), (x, height)], fill=(
            int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t),
        ))

    def _font(path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    font_lg = _font("C:/Windows/Fonts/msyh.ttc",  28)
    font_sm = _font("C:/Windows/Fonts/arial.ttf",  17)

    cx, cy = width // 2, height // 2
    draw.text((cx, cy - 30), "[ 占位图 · Placeholder ]", fill=(200, 200, 255), font=font_lg, anchor="mm")
    draw.text((cx, cy + 15), prompt[:72], fill=(160, 160, 220), font=font_sm, anchor="mm")
    draw.text(
        (cx, cy + 48),
        "将 API_PROVIDER 设为 siliconflow / openai / stability 可生成真实图像",
        fill=(100, 100, 160), font=font_sm, anchor="mm",
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── 硅基流动（国内直连，推荐）────────────────────────────────────────────────

async def _siliconflow(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    """
    硅基流动 API — https://siliconflow.cn
    默认使用 FLUX.1-schnell，可通过 SF_MODEL 环境变量覆盖。
    其他可用模型: stabilityai/stable-diffusion-3-5-large, Pro/black-forest-labs/FLUX.1-dev
    """
    if not API_KEY:
        raise RuntimeError("API_KEY 未设置，请在 .vscode/mcp.json 中填入硅基流动的 API Key")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.siliconflow.cn/v1/images/generations",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={
                "model":              SF_MODEL,
                "prompt":             prompt,
                "negative_prompt":    negative_prompt,
                "image_size":         f"{width}x{height}",
                "num_inference_steps": 20,
                "guidance_scale":     7.5,
            },
        )
        resp.raise_for_status()
        url = resp.json()["images"][0]["url"]
        img_resp = await client.get(url, timeout=60)
        img_resp.raise_for_status()
        return img_resp.content


# ── OpenAI DALL-E 3 ───────────────────────────────────────────────────────────

async def _openai_dalle(prompt: str, width: int, height: int) -> bytes:
    if not API_KEY:
        raise RuntimeError("API_KEY 未设置")

    # DALL-E 3 仅支持 1024x1024 / 1792x1024 / 1024x1792
    size = "1792x1024" if width >= height else "1024x1792"
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/v1/images/generations",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "response_format": "url"},
        )
        resp.raise_for_status()
        url = resp.json()["data"][0]["url"]
        img_resp = await client.get(url, timeout=60)
        return img_resp.content


# ── Stability AI ──────────────────────────────────────────────────────────────

async def _stability(prompt: str, negative_prompt: str, width: int, height: int) -> bytes:
    if not API_KEY:
        raise RuntimeError("API_KEY 未设置")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.stability.ai/v2beta/stable-image/generate/ultra",
            headers={"Authorization": f"Bearer {API_KEY}", "Accept": "image/*"},
            data={
                "prompt":          prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio":    "16:9",
                "output_format":   "png",
            },
        )
        resp.raise_for_status()
        return resp.content


# ── 入口 ──────────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
