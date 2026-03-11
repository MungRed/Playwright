#!/usr/bin/env python3
"""
Hunyuan MCP Server (Image)
==========================
仅暴露生图工具，具体实现复用 hunyuan_backend。
"""
import asyncio
from typing import cast

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

import hunyuan_backend

server = Server("playwright-image-gen")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="generate_image",
            description="为 Playwright 剧本阅读器生成场景背景图片（腾讯混元）并保存到 scripts/<script_name>/assets/ 目录。",
            inputSchema={
                "type": "object",
                "required": ["prompt", "filename"],
                "properties": {
                    "script_name": {
                        "type": "string",
                        "description": "剧本名（可选）。传入后会保存到 scripts/<script_name>/assets/ 目录。",
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
                        "default": hunyuan_backend.HUNYUAN_API_ACTION,
                    },
                    "scene_type": {
                        "type": "string",
                        "description": "场景类型：auto(自动推断) / background(背景图) / character(人物图)",
                        "enum": ["auto", "background", "character"],
                        "default": "auto",
                    },
                    "style_anchor": {
                        "type": "string",
                        "description": "风格锚点（可选）。传入后会优先用于当前生成并持久化到剧本 style contract。",
                    },
                    "negative_anchor": {
                        "type": "string",
                        "description": "负向风格锚点（可选）。用于统一排除项并持久化。",
                    },
                    "enforce_style": {
                        "type": "boolean",
                        "description": "是否强制拼接风格锚点，默认 true。",
                        "default": True,
                    },
                    "strict_no_people": {
                        "type": "boolean",
                        "description": "背景图是否强制无人物约束，默认 true。",
                        "default": True,
                    },
                    "retry_max": {
                        "type": "integer",
                        "description": "失败重试次数（覆盖环境变量 HUNYUAN_RETRY_MAX）。",
                    },
                    "reference_images": {
                        "type": "array",
                        "description": "图生图参考图列表（仅 SubmitTextToImageJob 可用，最多3项）。支持公网 URL，或在启用 COS_AUTO_UPLOAD_ENABLED 时传本地路径自动上传。",
                        "items": {"type": "string"},
                    },
                    "revise_prompt": {
                        "type": "boolean",
                        "description": "是否开启AI自动优化提示词（仅 SubmitTextToImageJob 可用，默认 true）。开启后模型会自动优化提示词以提升生成质量。对应API参数：Revise",
                        "default": True,
                    },
                    "logo_add": {
                        "type": "integer",
                        "description": "是否添加标识水印（仅 SubmitTextToImageJob 可用，默认 0）。0-不添加，1-添加。",
                        "enum": [0, 1],
                        "default": 0,
                    },
                },
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "generate_image":
        raise ValueError(f"未知工具: {name}")
    result = await hunyuan_backend.call_tool(name, arguments)
    return cast(list[types.TextContent], result)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
