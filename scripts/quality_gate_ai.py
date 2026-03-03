#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI质量门：使用混元AI评分替代定量指标"""
import argparse
import json
import subprocess
from pathlib import Path
import sys


def call_ai_scoring(script_path: Path) -> dict:
    """调用AI评分工具"""
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "quality_score_by_ai.py"), str(script_path)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode != 0:
        print(f"[ERROR] AI scoring failed (exit code {result.returncode})", file=sys.stderr)
        if result.stderr:
            print(f"stderr: {result.stderr[:200]}", file=sys.stderr)
        return None
    
    try:
        if not result.stdout or not result.stdout.strip():
            print(f"[ERROR] Empty stdout from AI scoring", file=sys.stderr)
            return None
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON from AI scoring: {e}", file=sys.stderr)
        print(f"stdout: {result.stdout[:200]}", file=sys.stderr)
        return None


def analyze_with_ai(script_path: Path) -> dict:
    """使用AI评分分析脚本"""
    report = call_ai_scoring(script_path)
    if not report:
        return {
            "script": script_path.as_posix(),
            "quality_gate": "error",
            "error": "AI评分失败"
        }
    
    # 基于AI评分生成质量门结果
    score = report.get("ai_score", 0)
    quality_gate = "pass" if score >= 70 else "rewrite_needed"
    
    return {
        "script": script_path.as_posix(),
        "ai_score": score,
        "dimension_scores": report.get("dimension_scores", {}),
        "quality_gate": quality_gate,
        "strengths": report.get("strengths", []),
        "improvements": report.get("improvements", []),
        "key_suggestion": report.get("key_suggestion", ""),
        "fail_fast_checks": {
            "ai_score_ok": score >= 70
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI质量门：基于混元AI评分")
    parser.add_argument("script_path", type=Path, help="目标 script.json 路径")
    parser.add_argument("--check", action="store_true", help="仅检查，未通过返回非0")
    parser.add_argument("--output", type=Path, help="可选：输出报告路径")
    args = parser.parse_args()
    
    if not args.script_path.exists():
        print(f"[ERROR] File not found: {args.script_path}")
        return 1
    
    result = analyze_with_ai(args.script_path)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    
    if args.check and result.get("quality_gate") != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
