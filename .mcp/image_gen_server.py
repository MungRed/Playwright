#!/usr/bin/env python3
"""
Image Generation MCP Server — Hunyuan Only
==========================================
通过 MCP 协议将腾讯混元生图能力暴露给 GitHub Copilot。
仅保留腾讯混元官方 API（TextToImageLite）调用逻辑。
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
HUNYUAN_RSP_IMG_TYPE = os.getenv("HUNYUAN_RSP_IMG_TYPE", "url")  # url | base64
HUNYUAN_API_ACTION = os.getenv("HUNYUAN_API_ACTION", "TextToImageLite")
HUNYUAN_JOB_TIMEOUT_SEC = int(os.getenv("HUNYUAN_JOB_TIMEOUT_SEC", "180"))
HUNYUAN_JOB_POLL_SEC = float(os.getenv("HUNYUAN_JOB_POLL_SEC", "2.0"))
HUNYUAN_RETRY_MAX = int(os.getenv("HUNYUAN_RETRY_MAX", "3"))
HUNYUAN_RETRY_BASE_SEC = float(os.getenv("HUNYUAN_RETRY_BASE_SEC", "1.5"))
OUTPUT_DIR = os.getenv(
    "OUTPUT_DIR",
    str(Path(__file__).parent.parent / "docs" / "scenes")
)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
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
    out_dir = Path(OUTPUT_DIR) / safe_script_name
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


def _is_retryable_error(message: str) -> bool:
    low = message.lower()
    markers = [
        "requestlimitexceeded",
        "jobnumexceed",
        "limitexceeded",
        "timeout",
        "temporarily unavailable",
        "connection reset",
        "read timed out",
    ]
    return any(m in low for m in markers)


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
