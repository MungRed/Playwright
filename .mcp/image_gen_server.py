#!/usr/bin/env python3
"""
Hunyuan MCP Server (Image + Text)
=================================
通过 MCP 协议将腾讯混元生图与生文能力暴露给 GitHub Copilot。
"""
import asyncio
import base64
import hashlib
import importlib
import json
import mimetypes
import os
import re
import time
from typing import Any, cast
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

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
HUNYUAN_TEXT_ENDPOINT = os.getenv("HUNYUAN_TEXT_ENDPOINT", "hunyuan.tencentcloudapi.com")
HUNYUAN_TEXT_MODEL = os.getenv("HUNYUAN_TEXT_MODEL", "hunyuan-pro")
HUNYUAN_RSP_IMG_TYPE = os.getenv("HUNYUAN_RSP_IMG_TYPE", "url")  # url | base64
HUNYUAN_API_ACTION = os.getenv("HUNYUAN_API_ACTION", "TextToImageLite")
HUNYUAN_JOB_TIMEOUT_SEC = int(os.getenv("HUNYUAN_JOB_TIMEOUT_SEC", "180"))
HUNYUAN_JOB_POLL_SEC = float(os.getenv("HUNYUAN_JOB_POLL_SEC", "2.0"))
HUNYUAN_RETRY_MAX = int(os.getenv("HUNYUAN_RETRY_MAX", "3"))
HUNYUAN_RETRY_BASE_SEC = float(os.getenv("HUNYUAN_RETRY_BASE_SEC", "1.5"))
OUTPUT_DIR = os.getenv(
    "OUTPUT_DIR",
    str(Path(__file__).parent.parent / "scripts")
)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
TEXT_SESSION_DIR = Path(OUTPUT_DIR) / "shared" / "text_sessions"
TEXT_SESSION_LOCK_WAIT_SEC = float(os.getenv("TEXT_SESSION_LOCK_WAIT_SEC", "8"))
TEXT_SESSION_LOCK_POLL_SEC = float(os.getenv("TEXT_SESSION_LOCK_POLL_SEC", "0.2"))
TEXT_SESSION_LOCK_STALE_SEC = float(os.getenv("TEXT_SESSION_LOCK_STALE_SEC", "120"))
STYLE_CONTRACT_FILE = "_style_contract.json"

DEFAULT_BG_STYLE_ANCHOR = (
    "anime visual novel background, clean lineart, soft global illumination, "
    "cinematic composition, consistent color grading"
)
DEFAULT_CHAR_STYLE_ANCHOR = (
    "anime visual novel character illustration, clean lineart, cel shading, "
    "stable character design, consistent color palette"
)
DEFAULT_NEGATIVE_ANCHOR = "低质量, 模糊, 水印, 文本, logo, 畸形, 多余肢体"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


COS_AUTO_UPLOAD_ENABLED = _env_bool("COS_AUTO_UPLOAD_ENABLED", False)
COS_SECRET_ID = os.getenv("COS_SECRET_ID", TENCENT_SECRET_ID)
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", TENCENT_SECRET_KEY)
COS_TOKEN = os.getenv("COS_TOKEN", TENCENT_TOKEN)
COS_REGION = os.getenv("COS_REGION", HUNYUAN_REGION)
COS_BUCKET = ""
COS_SCHEME = os.getenv("COS_SCHEME", "https")
COS_KEY_PREFIX = os.getenv("COS_KEY_PREFIX", "refs")
COS_PUBLIC_BASE_URL = os.getenv("COS_PUBLIC_BASE_URL", "").strip().rstrip("/")
COS_FORCE_SIGNED_URL = _env_bool("COS_FORCE_SIGNED_URL", False)
COS_SIGNED_URL_EXPIRE_SEC = int(os.getenv("COS_SIGNED_URL_EXPIRE_SEC", "3600"))


def _normalize_cos_bucket(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""

    if value.startswith("http://") or value.startswith("https://"):
        host = urlparse(value).netloc
        match = re.match(r"^(?P<bucket>[^.]+)\.cos\.[^.]+\.myqcloud\.com$", host)
        if match:
            return match.group("bucket")
        return ""

    return value


COS_BUCKET = _normalize_cos_bucket(os.getenv("COS_BUCKET", ""))

server = Server("playwright-image-gen")


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
                        "default": HUNYUAN_TEXT_MODEL,
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
        ),
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
                        "default": HUNYUAN_API_ACTION,
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
                },
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "generate_text":
        prompt = str(arguments.get("prompt", "")).strip()
        system_prompt = str(arguments.get("system_prompt", "")).strip()
        model = str(arguments.get("model", HUNYUAN_TEXT_MODEL)).strip() or HUNYUAN_TEXT_MODEL
        temperature = arguments.get("temperature")
        top_p = arguments.get("top_p")
        enable_enhancement = arguments.get("enable_enhancement")
        enable_deep_read = arguments.get("enable_deep_read")
        retry_max = int(arguments.get("retry_max", HUNYUAN_RETRY_MAX))
        session_id = str(arguments.get("session_id", "")).strip()
        reset_session = bool(arguments.get("reset_session", False))
        use_session_history = bool(arguments.get("use_session_history", True))
        max_session_messages = int(arguments.get("max_session_messages", 40))
        attach_file_ids_to_last_user = bool(arguments.get("attach_file_ids_to_last_user", True))
        carry_forward_file_ids = bool(arguments.get("carry_forward_file_ids", True))
        context_files_raw = arguments.get("context_files", []) or []
        if not isinstance(context_files_raw, list):
            context_files_raw = [str(context_files_raw)]

        lock_token = ""
        session_lock_wait_ms = 0
        if session_id:
            lock_token, session_lock_wait_ms = await _acquire_text_session_lock(
                session_id,
                wait_timeout_sec=TEXT_SESSION_LOCK_WAIT_SEC,
                poll_sec=TEXT_SESSION_LOCK_POLL_SEC,
                stale_sec=TEXT_SESSION_LOCK_STALE_SEC,
            )
            if not lock_token:
                result = {
                    "success": False,
                    "error": (
                        f"session_id={session_id} 当前正在被并发使用，已等待 {TEXT_SESSION_LOCK_WAIT_SEC:.1f}s 仍未获取锁。"
                        "请改为串行调用，或更换 session_id。"
                    ),
                    "session_id": session_id,
                    "session_lock_wait_ms": session_lock_wait_ms,
                }
                return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        try:
            messages = _normalize_chat_messages(arguments.get("messages", []), prompt, system_prompt)

            loaded_session_messages = 0
            if session_id and use_session_history:
                if reset_session:
                    _clear_text_session(session_id)
                prior_messages = _load_text_session(session_id)
                loaded_session_messages = len(prior_messages)
                messages = _merge_messages(prior_messages, messages, max_session_messages=max_session_messages)

                if carry_forward_file_ids and prior_messages:
                    carried_file_ids = _collect_recent_file_ids(prior_messages)
                    if carried_file_ids:
                        messages = _attach_file_ids_to_last_user_message(messages, carried_file_ids)

            uploaded_context_files: list[dict] = []
            context_file_ids: list[str] = []
            if context_files_raw:
                resolved_context_files, uploaded_context_files = await _resolve_context_files(
                    context_files_raw,
                    script_name=(session_id or "shared"),
                )
                context_file_ids = await _hunyuan_files_upload_with_retries(
                    resolved_context_files,
                    retry_max=max(0, retry_max),
                )
                if context_file_ids and attach_file_ids_to_last_user:
                    messages = _attach_file_ids_to_last_user_message(messages, context_file_ids)
                if enable_deep_read is None and context_file_ids:
                    enable_deep_read = True

            messages = _trim_messages(messages, max_session_messages=max_session_messages)

            text_result = await _hunyuan_text_with_retries(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                enable_enhancement=enable_enhancement,
                enable_deep_read=enable_deep_read,
                retry_max=max(0, retry_max),
            )

            persisted_messages = messages + [{"Role": "assistant", "Content": text_result.get("text", "")}]
            persisted_messages = _trim_messages(persisted_messages, max_session_messages=max_session_messages)
            if session_id:
                _save_text_session(session_id, persisted_messages)

            result = {
                "success": True,
                "provider": "hunyuan",
                "api_action": "ChatCompletions",
                "model": model,
                "messages": messages,
                "session_id": session_id or None,
                "loaded_session_messages": loaded_session_messages,
                "context_file_ids": context_file_ids,
                "uploaded_context_files": uploaded_context_files,
                "carry_forward_file_ids": carry_forward_file_ids,
                "session_lock_wait_ms": session_lock_wait_ms,
                **text_result,
            }
        except Exception as exc:
            result = {"success": False, "error": str(exc)}
        finally:
            if lock_token:
                _release_text_session_lock(session_id, lock_token)

        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    if name != "generate_image":
        raise ValueError(f"未知工具: {name}")

    script_name = str(arguments.get("script_name", "")).strip()
    prompt = arguments["prompt"]
    filename = arguments["filename"]
    negative_prompt = arguments.get("negative_prompt", "")
    width = int(arguments.get("width", 1280))
    height = int(arguments.get("height", 720))
    api_action = str(arguments.get("api_action", HUNYUAN_API_ACTION))
    scene_type_arg = str(arguments.get("scene_type", "auto")).strip().lower() or "auto"
    style_anchor_arg = str(arguments.get("style_anchor", "")).strip()
    negative_anchor_arg = str(arguments.get("negative_anchor", "")).strip()
    enforce_style = bool(arguments.get("enforce_style", True))
    strict_no_people = bool(arguments.get("strict_no_people", True))
    retry_max = int(arguments.get("retry_max", HUNYUAN_RETRY_MAX))
    reference_images_raw = arguments.get("reference_images", []) or []
    if not isinstance(reference_images_raw, list):
        reference_images_raw = [str(reference_images_raw)]

    safe_script_name = _sanitize_script_name(script_name)
    out_dir = Path(OUTPUT_DIR) / safe_script_name / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)
    style_contract_path = out_dir / STYLE_CONTRACT_FILE
    safe_filename = Path(filename).name
    out_path = out_dir / safe_filename
    scene_type = _infer_scene_type(safe_filename, scene_type_arg)
    normalized_width, normalized_height = _normalize_resolution(width, height, api_action)

    style_contract = _load_style_contract(style_contract_path)
    effective_style_anchor = _resolve_style_anchor(style_contract, scene_type, style_anchor_arg)
    effective_negative_anchor = _resolve_negative_anchor(style_contract, scene_type, negative_anchor_arg)

    if enforce_style and not effective_style_anchor:
        effective_style_anchor = DEFAULT_BG_STYLE_ANCHOR if scene_type == "background" else DEFAULT_CHAR_STYLE_ANCHOR
    if not effective_negative_anchor:
        effective_negative_anchor = DEFAULT_NEGATIVE_ANCHOR

    effective_prompt = _compose_prompt(prompt, scene_type, effective_style_anchor, enforce_style, strict_no_people)
    effective_negative_prompt = _compose_negative_prompt(
        negative_prompt,
        scene_type,
        effective_negative_anchor,
        strict_no_people,
    )

    try:
        resolved_refs, uploaded_refs = await _resolve_reference_images(reference_images_raw, safe_script_name)
        img_bytes = await _hunyuan_with_retries(
            prompt=effective_prompt,
            negative_prompt=effective_negative_prompt,
            width=normalized_width,
            height=normalized_height,
            api_action=api_action,
            reference_images=resolved_refs,
            retry_max=max(0, retry_max),
        )
        out_path.write_bytes(img_bytes)

        _update_style_contract(style_contract, scene_type, effective_style_anchor, effective_negative_anchor)
        _save_style_contract(style_contract_path, style_contract)

        result = {
            "success": True,
            "path": str(out_path),
            "script_name": safe_script_name,
            "provider": "hunyuan",
            "api_action": api_action,
            "scene_type": scene_type,
            "prompt": prompt,
            "effective_prompt": effective_prompt,
            "negative_prompt": effective_negative_prompt,
            "requested_size": f"{width}x{height}",
            "size": f"{normalized_width}x{normalized_height}",
            "style_contract": str(style_contract_path),
            "effective_style_anchor": effective_style_anchor,
            "effective_negative_anchor": effective_negative_anchor,
            "resolved_reference_images": resolved_refs,
            "uploaded_reference_images": uploaded_refs,
        }
    except Exception as exc:
        result = {"success": False, "error": str(exc)}

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _hunyuan_with_retries(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    api_action: str,
    reference_images: list[str],
    retry_max: int,
) -> bytes:
    attempt = 0
    while True:
        try:
            return await _hunyuan(
                prompt,
                negative_prompt,
                width,
                height,
                api_action=api_action,
                reference_images=reference_images,
            )
        except Exception as exc:
            msg = str(exc)
            if attempt >= retry_max or not _is_retryable_error(msg):
                raise
            sleep_sec = max(0.5, HUNYUAN_RETRY_BASE_SEC * (2 ** attempt))
            await asyncio.sleep(sleep_sec)
            attempt += 1


async def _hunyuan_text_with_retries(
    model: str,
    messages: list[dict],
    temperature: float | None,
    top_p: float | None,
    enable_enhancement: bool | None,
    enable_deep_read: bool | None,
    retry_max: int,
) -> dict:
    attempt = 0
    while True:
        try:
            return await _hunyuan_text(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                enable_enhancement=enable_enhancement,
                enable_deep_read=enable_deep_read,
            )
        except Exception as exc:
            msg = str(exc)
            if attempt >= retry_max or not _is_retryable_error(msg):
                raise
            sleep_sec = max(0.5, HUNYUAN_RETRY_BASE_SEC * (2 ** attempt))
            await asyncio.sleep(sleep_sec)
            attempt += 1


def _is_retryable_error(message: str) -> bool:
    low = message.lower()
    markers = [
        "requestlimitexceeded",
        "jobnumexceed",
        "limitexceeded",
        "timeout",
        "enginerequesttimeout",
        "engineservererror",
        "engineserverlimitexceeded",
        "temporarily unavailable",
        "connection reset",
        "read timed out",
    ]
    return any(m in low for m in markers)


def _normalize_chat_messages(messages_raw: object, prompt: str, system_prompt: str) -> list[dict]:
    normalized: list[dict] = []

    if isinstance(messages_raw, list) and messages_raw:
        for idx, item in enumerate(messages_raw, start=1):
            if not isinstance(item, dict):
                raise RuntimeError(f"messages[{idx}] 必须是对象")

            role = str(item.get("role") or item.get("Role") or "").strip().lower()
            content_obj = item.get("content")
            if content_obj is None:
                content_obj = item.get("Content")
            content = str(content_obj or "").strip()

            if role not in {"system", "user", "assistant", "tool"}:
                raise RuntimeError(f"messages[{idx}].role 非法：{role}")
            if not content:
                raise RuntimeError(f"messages[{idx}].content 不能为空")

            message: dict[str, Any] = {"Role": role, "Content": content}
            file_ids_raw = item.get("file_ids")
            if file_ids_raw is None:
                file_ids_raw = item.get("FileIDs")
            if file_ids_raw is not None:
                if not isinstance(file_ids_raw, list):
                    raise RuntimeError(f"messages[{idx}].file_ids 必须是字符串数组")
                file_ids = [str(file_id).strip() for file_id in file_ids_raw if str(file_id).strip()]
                if file_ids:
                    message["FileIDs"] = file_ids

            normalized.append(message)

        return normalized

    if system_prompt:
        normalized.append({"Role": "system", "Content": system_prompt})
    if prompt:
        normalized.append({"Role": "user", "Content": prompt})

    if not normalized:
        raise RuntimeError("prompt 为空且未提供有效 messages")

    return normalized


def _trim_messages(messages: list[dict], max_session_messages: int) -> list[dict]:
    max_len = max(2, min(40, int(max_session_messages or 40)))
    if len(messages) <= max_len:
        return messages

    first = messages[0]
    has_system = str(first.get("Role", "")).lower() == "system"
    if has_system:
        keep_tail = max(1, max_len - 1)
        return [first, *messages[-keep_tail:]]
    return messages[-max_len:]


def _merge_messages(history_messages: list[dict], current_messages: list[dict], max_session_messages: int) -> list[dict]:
    if not history_messages:
        return _trim_messages(current_messages, max_session_messages)

    merged = list(history_messages)
    merged.extend(current_messages)
    return _trim_messages(merged, max_session_messages)


def _session_file_path(session_id: str) -> Path:
    safe = _sanitize_script_name(session_id)
    TEXT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return TEXT_SESSION_DIR / f"{safe}.json"


def _session_lock_file_path(session_id: str) -> Path:
    safe = _sanitize_script_name(session_id)
    TEXT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return TEXT_SESSION_DIR / f"{safe}.lock"


def _read_session_lock_meta(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _try_create_text_session_lock(session_id: str, token: str) -> bool:
    path = _session_lock_file_path(session_id)
    payload = {"token": token, "created_at": time.time(), "pid": os.getpid()}

    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(path), flags)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return True
    except FileExistsError:
        return False


def _remove_stale_text_session_lock(session_id: str, stale_sec: float) -> bool:
    path = _session_lock_file_path(session_id)
    if not path.is_file():
        return False

    lock_meta = _read_session_lock_meta(path)
    created_at = float(lock_meta.get("created_at", 0) or 0)
    if created_at <= 0:
        return False

    if (time.time() - created_at) <= max(1.0, stale_sec):
        return False

    path.unlink(missing_ok=True)
    return True


async def _acquire_text_session_lock(
    session_id: str,
    wait_timeout_sec: float,
    poll_sec: float,
    stale_sec: float,
) -> tuple[str, int]:
    if not session_id:
        return "", 0

    start = time.time()
    timeout_sec = max(0.1, float(wait_timeout_sec or 0.1))
    step_sec = max(0.05, float(poll_sec or 0.05))
    token = f"{time.time_ns()}-{os.getpid()}"

    while (time.time() - start) <= timeout_sec:
        created = await asyncio.to_thread(_try_create_text_session_lock, session_id, token)
        if created:
            waited_ms = int((time.time() - start) * 1000)
            return token, waited_ms

        await asyncio.to_thread(_remove_stale_text_session_lock, session_id, stale_sec)
        await asyncio.sleep(step_sec)

    waited_ms = int((time.time() - start) * 1000)
    return "", waited_ms


def _release_text_session_lock(session_id: str, token: str) -> None:
    if not session_id or not token:
        return

    path = _session_lock_file_path(session_id)
    if not path.is_file():
        return

    lock_meta = _read_session_lock_meta(path)
    if str(lock_meta.get("token", "")) != str(token):
        return

    path.unlink(missing_ok=True)


def _load_text_session(session_id: str) -> list[dict]:
    if not session_id:
        return []

    path = _session_file_path(session_id)
    if not path.is_file():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            return []

        normalized: list[dict] = []
        for msg in payload:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("Role") or msg.get("role") or "").strip().lower()
            content = str(msg.get("Content") or msg.get("content") or "").strip()
            if role not in {"system", "user", "assistant", "tool"}:
                continue
            if not content:
                continue

            item: dict[str, Any] = {"Role": role, "Content": content}
            file_ids_raw = msg.get("FileIDs")
            if isinstance(file_ids_raw, list):
                file_ids = [str(file_id).strip() for file_id in file_ids_raw if str(file_id).strip()]
                if file_ids:
                    item["FileIDs"] = file_ids

            normalized.append(item)

        return normalized
    except Exception:
        return []


def _save_text_session(session_id: str, messages: list[dict]) -> None:
    if not session_id:
        return

    path = _session_file_path(session_id)
    path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_text_session(session_id: str) -> None:
    if not session_id:
        return

    path = _session_file_path(session_id)
    if path.is_file():
        path.unlink(missing_ok=True)


def _attach_file_ids_to_last_user_message(messages: list[dict], file_ids: list[str]) -> list[dict]:
    if not file_ids:
        return messages

    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if str(msg.get("Role", "")).lower() != "user":
            continue

        existing = msg.get("FileIDs")
        merged: list[str] = []
        if isinstance(existing, list):
            merged.extend([str(item).strip() for item in existing if str(item).strip()])
        merged.extend([str(item).strip() for item in file_ids if str(item).strip()])

        deduped: list[str] = []
        seen: set[str] = set()
        for item in merged:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)

        msg["FileIDs"] = deduped
        messages[idx] = msg
        return messages

    raise RuntimeError("未找到可附加 FileIDs 的 user 消息，请先提供 prompt 或 messages[user]")


def _collect_recent_file_ids(messages: list[dict], limit_messages: int = 20, limit_file_ids: int = 8) -> list[str]:
    if not messages:
        return []

    collected: list[str] = []
    seen: set[str] = set()
    inspected = 0

    for msg in reversed(messages):
        if inspected >= max(1, limit_messages):
            break
        inspected += 1

        if str(msg.get("Role", "")).lower() != "user":
            continue

        file_ids_raw = msg.get("FileIDs")
        if not isinstance(file_ids_raw, list):
            continue

        for file_id in file_ids_raw:
            norm = str(file_id).strip()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            collected.append(norm)
            if len(collected) >= max(1, limit_file_ids):
                return collected

    return collected


async def _resolve_context_files(context_files: list[str], script_name: str) -> tuple[list[dict], list[dict]]:
    resolved: list[dict] = []
    uploaded: list[dict] = []

    for raw in context_files:
        file_ref = str(raw).strip()
        if not file_ref:
            continue

        file_name = Path(file_ref).name or "context.txt"
        if _is_http_url(file_ref):
            resolved.append({"name": file_name, "url": file_ref})
            continue

        local_path = _resolve_local_path(file_ref)
        if local_path is None:
            raise RuntimeError(f"上下文文件既不是 URL，也不是可访问本地文件：{file_ref}")

        cos_url, existed = await asyncio.to_thread(_ensure_cos_reference_url, local_path, script_name)
        resolved.append({"name": local_path.name, "url": cos_url})
        uploaded.append(
            {
                "local_path": str(local_path),
                "cos_url": cos_url,
                "existed": existed,
            }
        )

    return resolved, uploaded


async def _hunyuan_files_upload_with_retries(files: list[dict], retry_max: int) -> list[str]:
    file_ids: list[str] = []
    for file_item in files:
        attempt = 0
        while True:
            try:
                file_id = await _hunyuan_upload_file(
                    name=str(file_item.get("name", "context.txt")),
                    url=str(file_item.get("url", "")),
                )
                if file_id:
                    file_ids.append(file_id)
                break
            except Exception as exc:
                msg = str(exc)
                if attempt >= retry_max or not _is_retryable_error(msg):
                    raise
                sleep_sec = max(0.5, HUNYUAN_RETRY_BASE_SEC * (2 ** attempt))
                await asyncio.sleep(sleep_sec)
                attempt += 1

    return file_ids


def _infer_scene_type(filename: str, explicit: str) -> str:
    if explicit in {"background", "character"}:
        return explicit
    low = filename.lower()
    if low.startswith("scene_"):
        return "background"
    if low.startswith("char_"):
        return "character"
    return "background"


def _normalize_resolution(width: int, height: int, api_action: str) -> tuple[int, int]:
    w = max(256, int(width))
    h = max(256, int(height))
    action = (api_action or "").strip()

    if action != "TextToImageLite":
        return w, h

    ratio = w / h
    if 0.9 <= ratio <= 1.1:
        return 1024, 1024
    if ratio > 1.1:
        return 1280, 720
    return 720, 1280


def _load_style_contract(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _resolve_style_anchor(style_contract: dict, scene_type: str, style_anchor_arg: str) -> str:
    if style_anchor_arg.strip():
        return style_anchor_arg.strip()

    if scene_type == "background":
        return str(
            style_contract.get("background_style_anchor")
            or style_contract.get("style_anchor")
            or ""
        ).strip()

    return str(
        style_contract.get("character_style_anchor")
        or style_contract.get("style_anchor")
        or ""
    ).strip()


def _resolve_negative_anchor(style_contract: dict, scene_type: str, negative_anchor_arg: str) -> str:
    if negative_anchor_arg.strip():
        return negative_anchor_arg.strip()

    if scene_type == "background":
        return str(
            style_contract.get("background_negative_anchor")
            or style_contract.get("negative_anchor")
            or ""
        ).strip()

    return str(
        style_contract.get("character_negative_anchor")
        or style_contract.get("negative_anchor")
        or ""
    ).strip()


def _update_style_contract(
    style_contract: dict,
    scene_type: str,
    style_anchor: str,
    negative_anchor: str,
) -> None:
    if scene_type == "background":
        style_contract["background_style_anchor"] = style_anchor
        style_contract["background_negative_anchor"] = negative_anchor
    else:
        style_contract["character_style_anchor"] = style_anchor
        style_contract["character_negative_anchor"] = negative_anchor

    style_contract["updated_at"] = datetime.now().isoformat(timespec="seconds")
    style_contract["last_scene_type"] = scene_type
    style_contract.pop("style_anchor", None)
    style_contract.pop("negative_anchor", None)


def _save_style_contract(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _compose_prompt(
    user_prompt: str,
    scene_type: str,
    style_anchor: str,
    enforce_style: bool,
    strict_no_people: bool,
) -> str:
    chunks: list[str] = []
    if user_prompt.strip():
        chunks.append(user_prompt.strip())

    if scene_type == "background" and strict_no_people:
        chunks.append("无人场景, 无人物, no people, no character")

    if enforce_style and style_anchor.strip():
        chunks.append(style_anchor.strip())

    return "，".join(chunks)


def _compose_negative_prompt(
    user_negative: str,
    scene_type: str,
    negative_anchor: str,
    strict_no_people: bool,
) -> str:
    chunks: list[str] = []
    if user_negative.strip():
        chunks.append(user_negative.strip())
    if negative_anchor.strip():
        chunks.append(negative_anchor.strip())
    if scene_type == "background" and strict_no_people:
        chunks.append("人物, 人影, 路人")
    return ", ".join(chunks)


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


async def _hunyuan_text(
    model: str,
    messages: list[dict],
    temperature: float | None,
    top_p: float | None,
    enable_enhancement: bool | None,
    enable_deep_read: bool | None,
) -> dict:
    """
    腾讯混元生文官方 API（ChatCompletions）
    文档：https://cloud.tencent.com/document/product/1729/105701
    """
    if not TENCENT_SECRET_ID or not TENCENT_SECRET_KEY:
        raise RuntimeError("未设置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY")

    try:
        from tencentcloud.hunyuan.v20230901 import models
    except Exception as exc:
        raise RuntimeError("缺少腾讯云 SDK 依赖，请安装 tencentcloud-sdk-python") from exc

    def _invoke() -> dict:
        client = _build_hunyuan_text_client()

        payload: dict = {
            "Model": model,
            "Messages": messages,
            "Stream": False,
        }

        if temperature is not None:
            payload["Temperature"] = float(temperature)
        if top_p is not None:
            payload["TopP"] = float(top_p)
        if enable_enhancement is not None:
            payload["EnableEnhancement"] = bool(enable_enhancement)
        if enable_deep_read is not None:
            payload["EnableDeepRead"] = bool(enable_deep_read)

        req = models.ChatCompletionsRequest()
        req.from_json_string(json.dumps(payload, ensure_ascii=False))

        resp = client.ChatCompletions(req)
        resp_payload = json.loads(cast(Any, resp).to_json_string())

        choices = resp_payload.get("Choices") or []
        text = ""
        finish_reason = ""
        if choices:
            first = choices[0] or {}
            finish_reason = str(first.get("FinishReason") or "")
            message = first.get("Message") or {}
            text = str(message.get("Content") or "")

        return {
            "text": text,
            "finish_reason": finish_reason,
            "usage": resp_payload.get("Usage"),
            "request_id": resp_payload.get("RequestId"),
            "id": resp_payload.get("Id"),
            "note": resp_payload.get("Note"),
            "raw": resp_payload,
        }

    return await asyncio.to_thread(_invoke)


async def _hunyuan_upload_file(name: str, url: str) -> str:
    if not url.strip():
        raise RuntimeError("文件上传 URL 不能为空")

    try:
        from tencentcloud.hunyuan.v20230901 import models
    except Exception as exc:
        raise RuntimeError("缺少腾讯云 SDK 依赖，请安装 tencentcloud-sdk-python") from exc

    def _invoke() -> str:
        client = _build_hunyuan_text_client()
        req = models.FilesUploadsRequest()
        req.Name = name or Path(urlparse(url).path).name or "context.txt"
        req.URL = url
        resp = client.FilesUploads(req)
        resp_payload = json.loads(cast(Any, resp).to_json_string())
        file_id = str(resp_payload.get("ID") or "").strip()
        if not file_id:
            raise RuntimeError("FilesUploads 未返回有效 ID")
        return file_id

    return await asyncio.to_thread(_invoke)


def _build_hunyuan_text_client():
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.hunyuan.v20230901 import hunyuan_client
    except Exception as exc:
        raise RuntimeError("缺少腾讯云 SDK 依赖，请安装 tencentcloud-sdk-python") from exc

    cred = credential.Credential(TENCENT_SECRET_ID, TENCENT_SECRET_KEY, TENCENT_TOKEN or None)

    http_profile = HttpProfile()
    http_profile.endpoint = HUNYUAN_TEXT_ENDPOINT

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile

    return hunyuan_client.HunyuanClient(cred, HUNYUAN_REGION, client_profile)


async def _resolve_reference_images(reference_images: list[str], script_name: str) -> tuple[list[str], list[dict]]:
    resolved: list[str] = []
    uploaded: list[dict] = []

    for ref in reference_images:
        ref_text = str(ref).strip()
        if not ref_text:
            continue
        if _is_http_url(ref_text):
            resolved.append(ref_text)
            continue

        local_path = _resolve_local_path(ref_text)
        if local_path is None:
            raise RuntimeError(f"参考图既不是 URL，也不是可访问本地文件：{ref_text}")

        cos_url, existed = await asyncio.to_thread(_ensure_cos_reference_url, local_path, script_name)
        resolved.append(cos_url)
        uploaded.append(
            {
                "local_path": str(local_path),
                "cos_url": cos_url,
                "existed": existed,
            }
        )

    return resolved[:3], uploaded


def _ensure_cos_reference_url(local_path: Path, script_name: str) -> tuple[str, bool]:
    if not COS_AUTO_UPLOAD_ENABLED:
        raise RuntimeError(
            "检测到本地 reference_images，但未开启 COS 自动上传。"
            "请在 .vscode/mcp.json 设置 COS_AUTO_UPLOAD_ENABLED=true，或直接传公网 URL。"
        )
    if not COS_BUCKET:
        raise RuntimeError("未设置 COS_BUCKET，无法自动上传本地参考图")
    if not COS_SECRET_ID or not COS_SECRET_KEY:
        raise RuntimeError("未设置 COS_SECRET_ID / COS_SECRET_KEY，无法自动上传本地参考图")

    try:
        qcloud_cos = importlib.import_module("qcloud_cos")
        cos_exception = importlib.import_module("qcloud_cos.cos_exception")
        CosConfig = qcloud_cos.CosConfig
        CosS3Client = qcloud_cos.CosS3Client
        CosServiceError = cos_exception.CosServiceError
        CosClientError = cos_exception.CosClientError
    except Exception as exc:
        raise RuntimeError("缺少 COS SDK 依赖，请安装 cos-python-sdk-v5") from exc

    config = CosConfig(
        Region=COS_REGION,
        SecretId=COS_SECRET_ID,
        SecretKey=COS_SECRET_KEY,
        Token=(COS_TOKEN or None),
        Scheme=COS_SCHEME,
    )
    client = CosS3Client(config)

    object_key = _build_cos_key(local_path, script_name)

    existed = False
    try:
        client.head_object(Bucket=COS_BUCKET, Key=object_key)
        existed = True
    except (CosServiceError, CosClientError):
        existed = False

    if not existed:
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        with local_path.open("rb") as fp:
            client.put_object(
                Bucket=COS_BUCKET,
                Key=object_key,
                Body=fp,
                ContentType=content_type,
            )

    if COS_FORCE_SIGNED_URL:
        url = client.get_presigned_url(
            Method="GET",
            Bucket=COS_BUCKET,
            Key=object_key,
            Expired=max(60, COS_SIGNED_URL_EXPIRE_SEC),
        )
    else:
        url = _build_cos_public_url(object_key)

    return url, existed


def _build_cos_key(local_path: Path, script_name: str) -> str:
    safe_script_name = _sanitize_script_name(script_name)
    digest = _file_sha256(local_path)[:16]
    file_name = re.sub(r"[^\w\-\.\u4e00-\u9fff]", "_", local_path.name)
    prefix = COS_KEY_PREFIX.strip("/")
    parts = [part for part in [prefix, safe_script_name] if part]
    key_prefix = "/".join(parts)
    if key_prefix:
        return f"{key_prefix}/{digest}_{file_name}"
    return f"{digest}_{file_name}"


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _build_cos_public_url(object_key: str) -> str:
    encoded_key = quote(object_key, safe="/")
    if COS_PUBLIC_BASE_URL:
        return f"{COS_PUBLIC_BASE_URL}/{encoded_key}"
    return f"{COS_SCHEME}://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{encoded_key}"


def _is_http_url(value: str) -> bool:
    low = value.lower()
    return low.startswith("http://") or low.startswith("https://")


def _resolve_local_path(value: str) -> Path | None:
    path = Path(value)
    if path.is_file():
        return path.resolve()

    candidate = (PROJECT_ROOT / value).resolve()
    if candidate.is_file():
        return candidate

    return None


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
