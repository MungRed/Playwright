#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path


def segment_text(segment: dict) -> str:
    lines = segment.get("display_break_lines")
    if isinstance(lines, list) and lines:
        return "\n".join(str(x) for x in lines if str(x).strip())
    return str(segment.get("text", "") or "")


def is_dialogue_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    return s.startswith("\"") or s.startswith("“") or s.startswith("『") or ("：" in s and len(s.split("：", 1)[0]) <= 8)


def analyze(script_path: Path) -> dict:
    data = json.loads(script_path.read_text(encoding="utf-8-sig"))
    segments = data.get("segments", [])
    total = len(segments)

    texts = [segment_text(s) for s in segments]
    lengths = [len(t.strip()) for t in texts]
    non_empty_lengths = [x for x in lengths if x > 0]

    dialogue_segments = 0
    pure_dialogue_segments = 0
    narration_segments = 0
    breakline_segments = 0
    typewriter_mismatch = 0

    speaker_list = []
    for s, text in zip(segments, texts):
        lines = [x.strip() for x in text.split("\n") if x.strip()]
        dialogue_lines = sum(1 for line in lines if is_dialogue_line(line))
        if dialogue_lines > 0:
            dialogue_segments += 1
        if lines and dialogue_lines == len(lines):
            pure_dialogue_segments += 1
        if lines and dialogue_lines < len(lines):
            narration_segments += 1

        if isinstance(s.get("display_break_lines"), list) and s.get("display_break_lines"):
            breakline_segments += 1

        if s.get("effect") == "typewriter" and s.get("speed") != 55:
            typewriter_mismatch += 1

        sp = s.get("speaker")
        if sp:
            speaker_list.append(str(sp))

    unique_speakers = sorted(set(speaker_list))

    max_same_speaker_streak = 0
    cur = 0
    prev = None
    for sp in [s.get("speaker") for s in segments]:
        if sp and sp == prev:
            cur += 1
        else:
            cur = 1 if sp else 0
        prev = sp
        max_same_speaker_streak = max(max_same_speaker_streak, cur)

    long_ratio = (sum(1 for x in lengths if x > 260) / total) if total else 0.0
    short_ratio = (sum(1 for x in lengths if 0 < x < 25) / total) if total else 0.0

    text_blob = "\n".join(t.strip() for t in texts if t.strip())
    repeats = 0
    if text_blob:
        grams = [text_blob[i : i + 12] for i in range(max(0, len(text_blob) - 12))]
        c = Counter(grams)
        repeats = sum(v - 1 for v in c.values() if v > 2)

    avg_len = (sum(non_empty_lengths) / len(non_empty_lengths)) if non_empty_lengths else 0
    stdev_len = statistics_stdev(non_empty_lengths)

    metrics = {
        "total_segments": total,
        "avg_chars_per_segment": round(avg_len, 2),
        "stdev_chars_per_segment": round(stdev_len, 2),
        "dialogue_segment_ratio": round(dialogue_segments / total, 3) if total else 0,
        "pure_dialogue_segment_ratio": round(pure_dialogue_segments / total, 3) if total else 0,
        "narration_segment_ratio": round(narration_segments / total, 3) if total else 0,
        "display_break_lines_ratio": round(breakline_segments / total, 3) if total else 0,
        "typewriter_speed_mismatch": typewriter_mismatch,
        "unique_speaker_count": len(unique_speakers),
        "max_same_speaker_streak": max_same_speaker_streak,
        "long_segment_ratio": round(long_ratio, 3),
        "short_segment_ratio": round(short_ratio, 3),
        "repeat_12gram_overflow": repeats,
    }

    issues = []
    def add_issue(code: str, severity: str, message: str):
        issues.append({"code": code, "severity": severity, "message": message})

    if total < 18:
        add_issue("SEGMENT_TOO_FEW", "high", "段落数偏少，长篇可读性与节奏层次不足（建议 >= 18）。")
    if metrics["pure_dialogue_segment_ratio"] > 0.25:
        add_issue("PURE_DIALOGUE_HIGH", "high", "纯对白段落比例过高，建议补充环境/动作/心理描写。")
    if metrics["narration_segment_ratio"] < 0.45:
        add_issue("NARRATION_LOW", "medium", "叙述承载偏低，信息主要靠对白推进，画面感不足。")
    if metrics["display_break_lines_ratio"] < 0.35:
        add_issue("PACING_BREAKLINES_LOW", "medium", "分步节奏段偏少，关键段可增加多次点击推进。")
    if metrics["display_break_lines_ratio"] > 0.9 and total >= 20:
        add_issue("PACING_BREAKLINES_UNIFORM", "low", "几乎全段使用分步节奏，建议保留一部分单步段形成节奏对比。")
    if metrics["long_segment_ratio"] > 0.2:
        add_issue("LONG_SEGMENTS_HIGH", "medium", "过长段落较多，建议拆分并用分步节奏字段控制信息释放。")
    if metrics["max_same_speaker_streak"] > 5:
        add_issue("SPEAKER_STREAK_LONG", "medium", "同一说话人连续过长，建议插入互动与场景反馈。")
    if metrics["dialogue_segment_ratio"] > 0.3 and metrics["unique_speaker_count"] < 2:
        add_issue("SPEAKER_ATTR_MISSING", "medium", "对白占比较高但 speaker 标注不足，建议补充角色归属提升可读性。")
    if metrics["typewriter_speed_mismatch"] > 0:
        add_issue("TYPEWRITER_SPEED_INVALID", "high", "存在 typewriter 速度不为55的段落。")
    if repeats > 80:
        add_issue("REPETITION_HIGH", "medium", "文本重复度偏高，建议改写模板句与重复句式。")

    score = 100
    for issue in issues:
        score -= {"high": 15, "medium": 8, "low": 4}[issue["severity"]]
    score = max(0, score)

    fail_fast_checks = {
        "typewriter_speed_ok": metrics["typewriter_speed_mismatch"] == 0,
        "pure_dialogue_ok": metrics["pure_dialogue_segment_ratio"] <= 0.25,
        "narration_ok": metrics["narration_segment_ratio"] >= 0.45,
        "segment_count_ok": metrics["total_segments"] >= 18,
    }

    return {
        "script": script_path.as_posix(),
        "score": score,
        "quality_gate": "pass" if score >= 70 and all(fail_fast_checks.values()) else "rewrite_needed",
        "metrics": metrics,
        "issues": issues,
        "fail_fast_checks": fail_fast_checks,
        "suggestions": suggestion_templates(issues),
    }


def suggestion_templates(issues: list[dict]) -> list[dict]:
    mapping = {
        "PURE_DIALOGUE_HIGH": ("纯对白", "将目标段落改写为‘动作+环境+对白+心理’四层结构，每段至少保留一行非对白叙述。"),
        "NARRATION_LOW": ("叙述不足", "在每个关键转折段补两句镜头化环境描写和一句心理描写，避免信息仅由对话承载。"),
        "LONG_SEGMENTS_HIGH": ("长段过多", "把>260字段拆为2-3个点击步，使用 display_break_lines 逐步释放信息。"),
        "SPEAKER_STREAK_LONG": ("角色互动弱", "连续同一speaker超过5段时，插入旁白观察或他人反应段。"),
        "REPETITION_HIGH": ("重复表达", "对高频模板句做同义改写，替换重复开头和句尾。"),
        "PACING_BREAKLINES_UNIFORM": ("节奏单一", "保留部分单步段落，避免所有段都采用多步点击导致节奏同质化。"),
        "SPEAKER_ATTR_MISSING": ("角色标注", "对关键对白段补充 speaker 字段，保证读者快速识别说话者。"),
        "TYPEWRITER_SPEED_INVALID": ("演出参数", "将 effect=typewriter 的 speed 统一为 55。"),
    }
    out = []
    for issue in issues:
        if issue["code"] in mapping:
            title, prompt = mapping[issue["code"]]
            out.append({"category": title, "rewrite_prompt": prompt})
    return out


def statistics_stdev(values: list[int]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def main() -> int:
    parser = argparse.ArgumentParser(description="审计剧本质量并输出可执行改写建议。")
    parser.add_argument("script_path", type=Path, help="目标 script.json 路径")
    parser.add_argument("--check", action="store_true", help="仅校验，未通过返回非0")
    parser.add_argument("--output", type=Path, help="可选：输出审计 JSON 路径")
    args = parser.parse_args()

    report = analyze(args.script_path)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)

    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")

    if args.check and report["quality_gate"] != "pass":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
