#!/usr/bin/env python3
"""
Hunyuan MCP Server (Text)
=========================
仅暴露生文工具，具体实现复用 hunyuan_backend。
"""
import asyncio
from typing import cast

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

import hunyuan_backend

server = Server("playwright-text-gen")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="generate_text",
            description="调用腾讯混元生文 ChatCompletions 接口生成文本。",
            inputSchema={
                "type": "object",
                "required": ["prompt"],
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "用户输入提示词（当未传 messages 时必填）。",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "系统提示词（可选）。",
                    },
                    "messages": {
                        "type": "array",
                        "description": "可选：完整消息数组。每项需包含 role/content。传入后优先于 prompt/system_prompt。",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    "model": {
                        "type": "string",
                        "description": "模型名，默认读取 HUNYUAN_TEXT_MODEL。",
                        "default": hunyuan_backend.HUNYUAN_TEXT_MODEL,
                    },
                    "temperature": {
                        "type": "number",
                        "description": "采样温度（0.0~2.0，可选）。",
                    },
                    "top_p": {
                        "type": "number",
                        "description": "核采样参数（0.0~1.0，可选）。",
                    },
                    "enable_enhancement": {
                        "type": "boolean",
                        "description": "功能增强开关（如搜索）。",
                    },
                    "enable_deep_read": {
                        "type": "boolean",
                        "description": "深度阅读开关（文件对话场景推荐开启）。",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "可选：会话ID。传入后会自动持久化并复用历史消息，适合长篇续写。",
                    },
                    "reset_session": {
                        "type": "boolean",
                        "description": "是否清空指定会话历史后再开始本次请求。",
                        "default": False,
                    },
                    "use_session_history": {
                        "type": "boolean",
                        "description": "是否在本次请求中注入该会话历史（默认 true）。",
                        "default": True,
                    },
                    "max_session_messages": {
                        "type": "integer",
                        "description": "会话保留的最大消息数（默认 40，超出将自动裁剪旧消息）。",
                        "default": 40,
                    },
                    "context_files": {
                        "type": "array",
                        "description": "可选：上下文文件列表（URL 或本地路径）。会自动上传到混元文件接口并挂载 FileIDs。",
                        "items": {"type": "string"},
                    },
                    "attach_file_ids_to_last_user": {
                        "type": "boolean",
                        "description": "是否将上传得到的 FileIDs 自动附加到最后一条 user 消息。",
                        "default": True,
                    },
                    "carry_forward_file_ids": {
                        "type": "boolean",
                        "description": "会话续写时是否自动继承历史中的 FileIDs 并附加到本轮最后一条 user 消息（默认 true）。",
                        "default": True,
                    },
                    "retry_max": {
                        "type": "integer",
                        "description": "失败重试次数（覆盖环境变量 HUNYUAN_RETRY_MAX）。",
                    },
                },
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "generate_text":
        raise ValueError(f"未知工具: {name}")
    result = await hunyuan_backend.call_tool(name, arguments)
    return cast(list[types.TextContent], result)


async def main():
    async with stdio_server() as (read_stream, write_stream):  # pyright: ignore[reportGeneralTypeIssues]
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
