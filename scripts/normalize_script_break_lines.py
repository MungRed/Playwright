#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def normalize_script(path: Path, check_only: bool = False) -> tuple[int, int]:
    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    segments = data.get("segments", [])

    changed = 0
    for segment in segments:
        segment_changed = False
        text = segment.get("text", "")
        break_lines = segment.get("display_break_lines")

        has_text = isinstance(text, str) and bool(text.strip())
        has_break_lines = isinstance(break_lines, list)

        normalized_lines: list[str] = []
        if has_break_lines and has_text:
            normalized_lines = [line.strip() for line in text.split("\n") if line.strip()]
        elif has_break_lines:
            normalized_lines = [str(line).strip() for line in break_lines if str(line).strip()]

        need_update = False

        if has_break_lines:
            if has_text:
                need_update = True
            if break_lines != normalized_lines:
                need_update = True
            if need_update and not check_only:
                segment["text"] = ""
                segment["display_break_lines"] = normalized_lines
        else:
            # 未使用分步字段时，保留 text-only 写法（可读性/节奏由创作策略决定）
            if isinstance(break_lines, list) and any(not isinstance(line, str) for line in break_lines):
                need_update = True
                if not check_only:
                    segment["display_break_lines"] = [str(line) for line in break_lines]

        if need_update:
            segment_changed = True

        effect = segment.get("effect")
        if effect == "typewriter" and segment.get("speed") != 55:
            if not check_only:
                segment["speed"] = 55
            segment_changed = True

        if segment_changed:
            changed += 1

    if changed and not check_only:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return changed, len(segments)


def main() -> int:
    parser = argparse.ArgumentParser(description="规范化剧本分步结构，并校验 typewriter 速度基线。")
    parser.add_argument("script_path", type=Path, help="目标 script.json 路径")
    parser.add_argument("--check", action="store_true", help="仅检查，不写回")
    args = parser.parse_args()

    changed, total = normalize_script(args.script_path, check_only=args.check)
    mode = "check" if args.check else "write"
    print(f"mode={mode} changed_segments={changed} total_segments={total}")

    if args.check and changed > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
