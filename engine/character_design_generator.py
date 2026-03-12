"""角色三视图生成器

为视觉小说角色生成三视图设定（front/left/right），建立外观一致性基准。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def generate_three_view_design(
    character_name: str,
    character_desc: str,
    style_anchor: str,
    script_name: str,
    script_root: Path | None = None,
) -> dict[str, str]:
    """生成角色三视图设定（front/left/right）

    Args:
        character_name: 角色名称（如"沈砚"）
        character_desc: 角色描述（如"男性, 30岁, 风衣, 忧郁气质"）
        style_anchor: 风格锚点（如"anime style, clean lineart"）
        script_name: 剧本名称（用于确定资源目录）
        script_root: 剧本根目录（默认为 scripts/{script_name}）

    Returns:
        包含三个视角图路径的字典：
        {
            "front": "assets/char_ref_沈砚_front.png",
            "left": "assets/char_ref_沈砚_left.png",
            "right": "assets/char_ref_沈砚_right.png"
        }

    Raises:
        RuntimeError: 生图失败时抛出
    """
    if script_root is None:
        script_root = Path("scripts") / script_name

    assets_dir = script_root / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    views = [
        ("front", "正面视角"),
        ("left", "左侧面视角"),
        ("right", "右侧面视角"),
    ]

    view_paths: dict[str, str] = {}

    for view_key, view_cn in views:
        # 构造提示词
        prompt = (
            f"{character_desc}, "
            f"{view_cn}, "
            f"角色设定单, 三视图, "
            f"{style_anchor}, "
            f"clean lineart, character turnaround sheet, "
            f"white background, reference sheet"
        )

        negative = (
            "背景, 多角色, 文字, 水印, 低质量, 模糊, "
            "environment, multiple characters, text, watermark"
        )

        filename = f"char_ref_{character_name}_{view_key}.png"
        output_path = assets_dir / filename

        # 调用MCP生图工具
        result = _call_mcp_generate_image(
            script_name=script_name,
            prompt=prompt,
            negative_prompt=negative,
            filename=filename,
            width=1280,
            height=720,  # 横版，用于设定图
            api_action="TextToImageLite",
        )

        if not result or "error" in result:
            raise RuntimeError(
                f"生成角色 {character_name} 的 {view_key} 视图失败: {result.get('error', '未知错误')}"
            )

        view_paths[view_key] = f"assets/{filename}"

    return view_paths


def _call_mcp_generate_image(
    script_name: str,
    prompt: str,
    negative_prompt: str,
    filename: str,
    width: int,
    height: int,
    api_action: str,
) -> dict[str, Any]:
    """调用MCP生图工具（直接导入hunyuan_backend）

    Returns:
        包含生成结果的字典，如：
        {
            "success": True,
            "path": "scripts/{script_name}/assets/{filename}",
            ...
        }
    """
    import asyncio

    # 导入hunyuan_backend
    mcp_path = Path(__file__).parent.parent / ".mcp"
    if str(mcp_path) not in sys.path:
        sys.path.insert(0, str(mcp_path))

    try:
        import hunyuan_backend
    except ImportError as e:
        raise RuntimeError(f"无法导入hunyuan_backend模块: {e}")

    # 构造调用参数
    arguments = {
        "script_name": script_name,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "filename": filename,
        "width": width,
        "height": height,
        "api_action": api_action,
    }

    # 调用async函数
    try:
        # 使用asyncio.run运行异步函数
        result_list = asyncio.run(hunyuan_backend.call_tool("generate_image", arguments))

        # 解析返回结果（MCP返回的是TextContent列表）
        if result_list and len(result_list) > 0:
            result_text = result_list[0].text
            result_dict = json.loads(result_text)
            return result_dict
        else:
            raise RuntimeError("MCP调用返回空结果")

    except Exception as e:
        raise RuntimeError(f"MCP生图调用失败: {e}")


def composite_three_views(
    view_paths: dict[str, str],
    output_path: Path,
    script_root: Path | None = None,
) -> Path:
    """合成三视图为单张图片（可选功能）

    Args:
        view_paths: 包含front/left/right路径的字典
        output_path: 输出合成图路径
        script_root: 剧本根目录

    Returns:
        合成图的绝对路径

    注意：此功能需要PIL库，若未安装则跳过合成，直接返回front视图
    """
    try:
        from PIL import Image
    except ImportError:
        print("警告: PIL未安装，跳过三视图合成，使用front视图作为代表")
        # 返回front视图路径（不合成）
        return Path(view_paths["front"])

    if script_root is None:
        script_root = Path("scripts")

    # 加载三个视图
    images = []
    for view_key in ["front", "left", "right"]:
        img_path = script_root / view_paths[view_key]
        if not img_path.exists():
            raise FileNotFoundError(f"视图文件不存在: {img_path}")
        images.append(Image.open(img_path))

    # 简单水平拼接
    widths, heights = zip(*(img.size for img in images))
    total_width = sum(widths)
    max_height = max(heights)

    composite = Image.new("RGB", (total_width, max_height), (255, 255, 255))

    x_offset = 0
    for img in images:
        composite.paste(img, (x_offset, 0))
        x_offset += img.width

    # 保存合成图
    composite.save(output_path)
    return output_path


# 命令行接口（用于测试）
def main():
    """命令行测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="生成角色三视图")
    parser.add_argument("character_name", help="角色名称")
    parser.add_argument("character_desc", help="角色描述")
    parser.add_argument("script_name", help="剧本名称")
    parser.add_argument("--style", default="anime style, clean lineart", help="风格锚点")
    parser.add_argument("--composite", action="store_true", help="是否合成三视图")

    args = parser.parse_args()

    print(f"正在为 {args.character_name} 生成三视图...")

    view_paths = generate_three_view_design(
        character_name=args.character_name,
        character_desc=args.character_desc,
        style_anchor=args.style,
        script_name=args.script_name,
    )

    print(f"三视图生成完成:")
    for view_key, path in view_paths.items():
        print(f"  {view_key}: {path}")

    if args.composite:
        script_root = Path("scripts") / args.script_name
        output_path = script_root / "assets" / f"char_ref_{args.character_name}_three_view.png"
        composite_path = composite_three_views(view_paths, output_path, script_root)
        print(f"合成图: {composite_path}")


if __name__ == "__main__":
    main()
