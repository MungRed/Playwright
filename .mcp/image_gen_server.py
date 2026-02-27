#!/usr/bin/env python3
"""
Image Generation MCP Server — Hunyuan Only
==========================================
通过 MCP 协议将腾讯混元生图能力暴露给 GitHub Copilot。
仅保留腾讯混元官方 API（TextToImageLite）调用逻辑。
"""
import asyncio
import base64
import json
import os
import re
import time
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── 配置（从环境变量读取）─────────────────────────────────────────────────────────
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID", "")
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY", "")
TENCENT_TOKEN = os.getenv("TENCENT_TOKEN", "")
HUNYUAN_REGION = os.getenv("HUNYUAN_REGION", "ap-guangzhou")
HUNYUAN_ENDPOINT = os.getenv("HUNYUAN_ENDPOINT", "aiart.tencentcloudapi.com")
HUNYUAN_RSP_IMG_TYPE = os.getenv("HUNYUAN_RSP_IMG_TYPE", "url")  # url | base64
HUNYUAN_API_ACTION = os.getenv("HUNYUAN_API_ACTION", "TextToImageLite")
HUNYUAN_JOB_TIMEOUT_SEC = int(os.getenv("HUNYUAN_JOB_TIMEOUT_SEC", "180"))
HUNYUAN_JOB_POLL_SEC = float(os.getenv("HUNYUAN_JOB_POLL_SEC", "2.0"))
OUTPUT_DIR = os.getenv(
    "OUTPUT_DIR",
    str(Path(__file__).parent.parent / "docs" / "scenes")
)

server = Server("playwright-image-gen")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="generate_image",
            description="为 Playwright 剧本阅读器生成场景背景图片（腾讯混元）并保存到 docs/scenes/ 目录。",
            inputSchema={
                "type": "object",
                "required": ["prompt", "filename"],
                "properties": {
                    "script_name": {
                        "type": "string",
                        "description": "剧本名（可选）。传入后会保存到 docs/scenes/<script_name>/ 目录。",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "图像描述 Prompt（推荐中文）。例如：'雨夜竹林小路，电影感，薄雾'",
                    },
                    "filename": {
                        "type": "string",
                        "description": "保存的文件名（不含路径），例如：'forest_night.png'",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "反向提示词（可选）",
                        "default": "低质量, 模糊, 水印, 文本",
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
                    "api_action": {
                        "type": "string",
                        "description": "混元接口：TextToImageLite（极速版）或 SubmitTextToImageJob（3.0任务）",
                        "enum": ["TextToImageLite", "SubmitTextToImageJob"],
                        "default": HUNYUAN_API_ACTION,
                    },
                    "reference_images": {
                        "type": "array",
                        "description": "图生图参考图 URL 列表（仅 SubmitTextToImageJob 可用，最多3张）",
                        "items": {"type": "string"},
                    },
                },
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "generate_image":
        raise ValueError(f"未知工具: {name}")

    script_name = str(arguments.get("script_name", "")).strip()
    prompt = arguments["prompt"]
    filename = arguments["filename"]
    negative_prompt = arguments.get("negative_prompt", "")
    width = int(arguments.get("width", 1280))
    height = int(arguments.get("height", 720))
    api_action = str(arguments.get("api_action", HUNYUAN_API_ACTION))
    reference_images = arguments.get("reference_images", []) or []

    safe_script_name = _sanitize_script_name(script_name)
    out_dir = Path(OUTPUT_DIR) / safe_script_name
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = Path(filename).name
    out_path = out_dir / safe_filename

    try:
        img_bytes = await _hunyuan(
            prompt,
            negative_prompt,
            width,
            height,
            api_action=api_action,
            reference_images=reference_images,
        )
        out_path.write_bytes(img_bytes)
        result = {
            "success": True,
            "path": str(out_path),
            "script_name": safe_script_name,
            "provider": "hunyuan",
            "api_action": api_action,
            "prompt": prompt,
            "size": f"{width}x{height}",
        }
    except Exception as exc:
        result = {"success": False, "error": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _hunyuan(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    api_action: str,
    reference_images: list[str],
) -> bytes:
    """
    腾讯混元官方 API（TextToImageLite）
    文档：https://cloud.tencent.com/document/product/1668/120721
    """
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("未设置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY")

    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.aiart.v20221229 import aiart_client, models
    except Exception as exc:
        raise RuntimeError("缺少腾讯云 SDK 依赖，请安装 tencentcloud-sdk-python") from exc

    def _build_client():
        cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_TOKEN or None)

        http_profile = HttpProfile()
        http_profile.endpoint = HUNYUAN_ENDPOINT

        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile

        return aiart_client.AiartClient(cred, HUNYUAN_REGION, client_profile)

    def _invoke_lite() -> tuple[str, str]:
        client = _build_client()
        req = models.TextToImageLiteRequest()
        req.Prompt = prompt
        if negative_prompt:
            req.NegativePrompt = negative_prompt
        req.Resolution = f"{width}:{height}"
        req.RspImgType = HUNYUAN_RSP_IMG_TYPE

        resp = client.TextToImageLite(req)
        result_image_obj: object = getattr(resp, "ResultImage", None)
        if not result_image_obj:
            raise RuntimeError("腾讯混元响应缺少 ResultImage")
        return str(result_image_obj), HUNYUAN_RSP_IMG_TYPE.lower()

    def _invoke_submit_job() -> tuple[str, str]:
        client = _build_client()

        req = models.SubmitTextToImageJobRequest()
        req.Prompt = prompt
        req.Resolution = f"{width}:{height}"
        if reference_images:
            req.Images = reference_images[:3]

        submit_resp = client.SubmitTextToImageJob(req)
        job_id = str(getattr(submit_resp, "JobId", ""))
        if not job_id:
            raise RuntimeError("SubmitTextToImageJob 未返回 JobId")

        deadline = time.monotonic() + max(30, HUNYUAN_JOB_TIMEOUT_SEC)
        while time.monotonic() < deadline:
            query_req = models.QueryTextToImageJobRequest()
            query_req.JobId = job_id
            query_resp = client.QueryTextToImageJob(query_req)

            status = str(getattr(query_resp, "JobStatusCode", ""))
            if status == "5":
                images = getattr(query_resp, "ResultImage", None) or []
                if not images:
                    raise RuntimeError("QueryTextToImageJob 返回成功但无 ResultImage")
                return str(images[0]), "url"

            if status == "4":
                err_msg = str(getattr(query_resp, "JobErrorMsg", "未知错误"))
                err_code = str(getattr(query_resp, "JobErrorCode", ""))
                raise RuntimeError(f"混元3.0任务失败：{err_code} {err_msg}".strip())

            time.sleep(max(0.5, HUNYUAN_JOB_POLL_SEC))

        raise RuntimeError("混元3.0任务查询超时，请稍后重试")

    action = api_action.strip() or HUNYUAN_API_ACTION
    if action == "TextToImageLite":
        result_image, result_mode = await asyncio.to_thread(_invoke_lite)
    elif action == "SubmitTextToImageJob":
        result_image, result_mode = await asyncio.to_thread(_invoke_submit_job)
    else:
        raise RuntimeError(f"不支持的 api_action: {action}")

    if result_mode == "base64":
        try:
            return base64.b64decode(result_image)
        except Exception as exc:
            raise RuntimeError("腾讯混元返回的 base64 图片解码失败") from exc

    async with httpx.AsyncClient(timeout=60) as client:
        img_resp = await client.get(result_image)
        img_resp.raise_for_status()
        return img_resp.content


def _sanitize_script_name(script_name: str) -> str:
    if not script_name:
        return "shared"
    name = script_name.strip().replace(" ", "_")
    name = re.sub(r"[^\w\-\u4e00-\u9fff]", "_", name)
    name = re.sub(r"_+", "_", name).strip("._-")
    return name or "shared"


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
