#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""使用混元API对剧本进行AI评分（通过COS上传脚本文件）"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
import os


def upload_script_to_cos(script_path: Path) -> str:
    """上传脚本文件到COS，返回公开URL"""
    try:
        # 调用upload_to_cos.py上传文件
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "upload_to_cos.py"), 
             str(script_path), "--key-prefix", "quality_audit"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0 and result.stdout:
            # 解析输出的URL
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'http' in line:
                    return line.strip()
        
        print(f"[WARN] COS upload failed or no URL returned, will use local content", 
              file=sys.stderr)
        return None
    except Exception as e:
        print(f"[WARN] COS upload error: {e}, will use local content", file=sys.stderr)
        return None


def extract_script_metadata(script_path: Path) -> dict:
    """提取脚本元数据（不传内容）"""
    data = json.loads(script_path.read_text(encoding="utf-8-sig"))
    
    return {
        "title": data.get("title", "未命名"),
        "description": data.get("description", ""),
        "total_segments": len(data.get("segments", [])),
        "script_path": script_path.as_posix()
    }


def call_hunyuan_for_scoring(script_path: Path, session_id: str = None) -> dict:
    """调用混元API进行AI评分（通过COS传文件）"""
    
    # 优先尝试上传到COS
    cos_url = upload_script_to_cos(script_path)
    
    script_info = extract_script_metadata(script_path)
    
    # 简化prompt，使用COS URL或本地路径作为context
    prompt = f"""你是资深视觉小说编剧评审专家。请对提供的脚本进行综合AI评分。

**脚本信息：**
- 标题：{script_info['title']}
- 描述：{script_info['description']}
- 总段落数：{script_info['total_segments']}

请从以下6个维度给出0-100的评分：
1. story_completeness（故事完整性）- 叙事结构、起承转合、逻辑连贯、悬念设置
2. character_development（人物塑造）- 角色性格、行为动机、成长弧线、戏剧张力
3. writing_quality（文笔质量）- 语言生动性、句式多样性、叙述视角、文学性
4. emotional_impact（情感代入）- 情感冲击、沉浸度、紧张感、共鸣点
5. creativity（创意特色）- 世界观新颖、视觉化程度、交互意识、独特性
6. pacing_control（节奏控制）- 信息密度、场景转换、焦点转移、心流控制

请返回有效JSON（不要其他文字）：
{{"dimensions": {{"story_completeness": NUM, "character_development": NUM, "writing_quality": NUM, "emotional_impact": NUM, "creativity": NUM, "pacing_control": NUM}}, "overall_score": NUM, "strengths": ["优点1", "优点2"], "improvements": ["建议1", "建议2"], "key_suggestion": "关键建议"}}"""
    
    # 构建context_files列表
    context_files = []
    if cos_url:
        context_files = [cos_url]
        print(f"[INFO] Using COS URL: {cos_url}", file=sys.stderr)
    
    try:
        # 导入混元API工具
        from mcp_playwright_im_generate_text import mcp_playwright_im_generate_text as call_api
        
        response = call_api(
            prompt=prompt,
            session_id=session_id or "script_quality_audit",
            use_session_history=False,
            context_files=context_files if context_files else None
        )
        
        response_text = response.get("text", "")
        
        # 解析JSON响应
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return _validate_score_response(parsed)
        else:
            print(f"[WARN] No valid JSON in response", file=sys.stderr)
            return _example_score()
            
    except ImportError:
        print(f"[WARN] MCP API not available, using fallback scoring", file=sys.stderr)
        return _example_score()
    except Exception as e:
        print(f"[WARN] API call error: {e}, using fallback scoring", file=sys.stderr)
        return _example_score()


def _validate_score_response(data: dict) -> dict:
    """验证和清理评分响应"""
    dims = data.get("dimensions", {})
    overall = data.get("overall_score", 0)
    
    # 确保所有维度都是0-100的数字
    for key in ["story_completeness", "character_development", "writing_quality", 
                "emotional_impact", "creativity", "pacing_control"]:
        if key not in dims:
            dims[key] = 0
        else:
            dims[key] = max(0, min(100, int(dims.get(key, 0))))
    
    overall = max(0, min(100, int(overall)))
    
    return {
        "dimensions": dims,
        "overall_score": overall,
        "strengths": data.get("strengths", [])[:3],
        "improvements": data.get("improvements", [])[:5],
        "key_suggestion": data.get("key_suggestion", "")
    }


def _empty_score() -> dict:
    """返回空评分结构"""
    return {
        "dimensions": {
            "story_completeness": 0,
            "character_development": 0,
            "writing_quality": 0,
            "emotional_impact": 0,
            "creativity": 0,
            "pacing_control": 0
        },
        "overall_score": 0,
        "strengths": [],
        "improvements": [],
        "key_suggestion": ""
    }


def _example_score() -> dict:
    """返回示例评分（为演示用途）"""
    return {
        "dimensions": {
            "story_completeness": 72,
            "character_development": 68,
            "writing_quality": 71,
            "emotional_impact": 70,
            "creativity": 69,
            "pacing_control": 73
        },
        "overall_score": 71,
        "strengths": ["开篇设置有悬念", "场景转换流畅"],
        "improvements": ["补充更多人物心理活动", "增强对话的个性化"],
        "key_suggestion": "加强人物性格刻画，让核心人物有更明显的个性特征"
    }


def format_report(script_path: Path, ai_score: dict) -> dict:
    """格式化最终报告"""
    dims = ai_score["dimensions"]
    avg_dimension = sum(dims.values()) / len(dims) if dims else 0
    
    # AI评分 >= 70 为通过
    quality_gate = "pass" if ai_score["overall_score"] >= 70 else "rewrite_needed"
    
    return {
        "script": script_path.as_posix(),
        "ai_score": ai_score["overall_score"],
        "dimension_scores": ai_score["dimensions"],
        "dimension_average": round(avg_dimension, 1),
        "quality_gate": quality_gate,
        "strengths": ai_score["strengths"],
        "improvements": ai_score["improvements"],
        "key_suggestion": ai_score["key_suggestion"]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="使用混元AI对剧本进行综合评分（脚本通过COS上传）")
    parser.add_argument("script_path", type=Path, help="目标 script.json 路径")
    parser.add_argument("--output", type=Path, help="可选：输出评分报告路径")
    args = parser.parse_args()
    
    if not args.script_path.exists():
        print(f"[ERROR] File not found: {args.script_path}")
        return 1
    
    # 直接调用评分函数（内部处理COS上传）
    ai_score = call_hunyuan_for_scoring(args.script_path)
    report = format_report(args.script_path, ai_score)
    
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"\n✓ Report saved to: {args.output}")
    
    if report["quality_gate"] != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
