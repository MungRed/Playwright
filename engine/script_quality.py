from __future__ import annotations

import copy
import json
import math
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

NARRATION_SPEAKER = "旁白"
DEFAULT_TYPEWRITER_SPEED = 55


@dataclass
class QualityIssue:
    level: str
    code: str
    message: str
    location: str


@dataclass
class QualityStats:
    storyboard_count: int
    script_count: int
    narration_count: int
    narration_ratio: float
    max_text_len: int


@dataclass
class QualityReport:
    passed: bool
    stats: QualityStats
    issues: list[QualityIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "stats": asdict(self.stats),
            "issues": [asdict(i) for i in self.issues],
        }


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunk_text(text: str, max_len: int = 80) -> list[str]:
    text = (text or "").strip()
    if not text:
        return [""]
    if len(text) <= max_len:
        return [text]

    # 先按标点切句，再按长度约束组装，最后做硬切分兜底。
    sentence_buf = ""
    sentences: list[str] = []
    for ch in text:
        sentence_buf += ch
        if ch in "。！？；,.!?;\n":
            s = sentence_buf.strip()
            if s:
                sentences.append(s)
            sentence_buf = ""
    if sentence_buf.strip():
        sentences.append(sentence_buf.strip())

    packed: list[str] = []
    cur = ""
    for s in sentences:
        if not cur:
            cur = s
            continue
        if len(cur) + len(s) <= max_len:
            cur += s
        else:
            packed.append(cur)
            cur = s
    if cur:
        packed.append(cur)

    out: list[str] = []
    for block in packed:
        while len(block) > max_len:
            out.append(block[:max_len].strip())
            block = block[max_len:]
        if block.strip():
            out.append(block.strip())
    return out or [text[:max_len]]


def _iter_scripts(data: dict[str, Any]):
    for sb_index, sb in enumerate(data.get("storyboards", [])):
        scripts = sb.get("scripts", []) if isinstance(sb, dict) else []
        for sc_index, sc in enumerate(scripts):
            yield sb_index, sc_index, sb, sc


def analyze_script_quality(data: dict[str, Any], min_narration_ratio: float = 0.40) -> QualityReport:
    issues: list[QualityIssue] = []

    storyboards = data.get("storyboards")
    if not isinstance(storyboards, list) or not storyboards:
        issues.append(QualityIssue("error", "STORYBOARDS_EMPTY", "storyboards 为空或不存在", "storyboards"))
        stats = QualityStats(0, 0, 0, 0.0, 0)
        return QualityReport(False, stats, issues)

    sb_ids: set[str] = set()
    seg_ids: set[str] = set()
    total = 0
    narr = 0
    max_text_len = 0

    for sb_index, sb in enumerate(storyboards):
        sb_loc = f"storyboards[{sb_index}]"
        sb_id = str(sb.get("id", "")).strip()
        if not sb_id:
            issues.append(QualityIssue("error", "SB_ID_MISSING", "分镜缺少 id", sb_loc))
        elif sb_id in sb_ids:
            issues.append(QualityIssue("error", "SB_ID_DUP", f"重复分镜 id: {sb_id}", sb_loc))
        else:
            sb_ids.add(sb_id)

        scripts = sb.get("scripts")
        if not isinstance(scripts, list) or not scripts:
            issues.append(QualityIssue("error", "SCRIPTS_EMPTY", "分镜 scripts 为空", sb_loc + ".scripts"))
            continue

        sb_total = 0
        sb_narr = 0
        first_speaker = str(scripts[0].get("speaker", "")).strip() if scripts else ""
        if first_speaker != NARRATION_SPEAKER:
            issues.append(QualityIssue("warn", "SB_NOT_START_WITH_NARRATION", "分镜未以旁白开头", sb_loc + ".scripts[0]"))

        for sc_index, sc in enumerate(scripts):
            sc_loc = f"{sb_loc}.scripts[{sc_index}]"
            seg_id = str(sc.get("id", "")).strip()
            speaker = str(sc.get("speaker", "")).strip()
            text = str(sc.get("text", ""))
            max_text_len = max(max_text_len, len(text))

            if not seg_id:
                issues.append(QualityIssue("error", "SEG_ID_MISSING", "段落缺少 id", sc_loc))
            elif seg_id in seg_ids:
                issues.append(QualityIssue("error", "SEG_ID_DUP", f"重复段落 id: {seg_id}", sc_loc))
            else:
                seg_ids.add(seg_id)

            if not speaker:
                issues.append(QualityIssue("error", "SPEAKER_MISSING", "段落缺少 speaker", sc_loc))

            if len(text) > 80:
                issues.append(QualityIssue("warn", "TEXT_TOO_LONG", f"text 长度 {len(text)} > 80", sc_loc))

            if speaker == NARRATION_SPEAKER:
                sb_narr += 1
                if sc.get("character_image") not in (None, "", "null"):
                    issues.append(QualityIssue("warn", "NARRATION_HAS_IMAGE", "旁白不应配置立绘", sc_loc))
            else:
                if not sc.get("character_image"):
                    issues.append(QualityIssue("warn", "DIALOGUE_NO_IMAGE", "对话缺少 character_image", sc_loc))

            if str(sc.get("effect", "typewriter")).lower() == "typewriter" and int(sc.get("speed", 55)) != 55:
                issues.append(QualityIssue("warn", "TYPEWRITER_SPEED", "typewriter 段落 speed 应为 55", sc_loc))

            sb_total += 1
            total += 1

        sb_ratio = (sb_narr / sb_total) if sb_total else 0.0
        narr += sb_narr
        if sb_ratio < min_narration_ratio:
            issues.append(
                QualityIssue(
                    "warn",
                    "SB_NARRATION_RATIO_LOW",
                    f"分镜旁白占比 {sb_ratio:.2f} < {min_narration_ratio:.2f}",
                    sb_loc,
                )
            )

    ratio = (narr / total) if total else 0.0
    if ratio < min_narration_ratio:
        issues.append(
            QualityIssue(
                "warn",
                "GLOBAL_NARRATION_RATIO_LOW",
                f"全局旁白占比 {ratio:.2f} < {min_narration_ratio:.2f}",
                "storyboards",
            )
        )

    passed = not any(i.level == "error" for i in issues)
    stats = QualityStats(len(storyboards), total, narr, ratio, max_text_len)
    return QualityReport(passed, stats, issues)


def _extract_narration_candidates(novel_text: str) -> deque[str]:
    blocks = [b.strip() for b in novel_text.replace("\r\n", "\n").split("\n\n") if b.strip()]
    out: deque[str] = deque()
    for block in blocks:
        for chunk in _chunk_text(block, 80):
            if chunk:
                out.append(chunk)
    if not out:
        out.append("雨声贴着棚檐滑落，空气里浮着潮湿的铁锈味。")
    return out


def _required_insertions(current_total: int, current_narr: int, target_ratio: float) -> int:
    # (n + x) / (c + x) >= t
    need = (target_ratio * current_total - current_narr) / max(1e-9, (1.0 - target_ratio))
    return max(0, int(math.ceil(need)))


def enrich_narration_with_novel(
    data: dict[str, Any],
    novel_text: str,
    target_ratio: float = 0.40,
) -> dict[str, Any]:
    result = copy.deepcopy(data)
    candidates = _extract_narration_candidates(novel_text)

    for sb in result.get("storyboards", []):
        scripts = sb.get("scripts", [])
        if not isinstance(scripts, list) or not scripts:
            continue

        narr = sum(1 for s in scripts if str(s.get("speaker", "")).strip() == NARRATION_SPEAKER)
        total = len(scripts)
        need = _required_insertions(total, narr, target_ratio)
        if need <= 0:
            continue

        insert_positions = [i for i, s in enumerate(scripts) if str(s.get("speaker", "")).strip() != NARRATION_SPEAKER]
        if not insert_positions:
            continue

        inserted = 0
        pos_cursor = 0
        while inserted < need:
            text = candidates[0]
            candidates.rotate(-1)
            pos = insert_positions[pos_cursor % len(insert_positions)] + inserted
            scripts.insert(
                pos,
                {
                    "id": "",
                    "speaker": NARRATION_SPEAKER,
                    "text": text,
                    "character_image": None,
                    "effect": "typewriter",
                    "speed": DEFAULT_TYPEWRITER_SPEED,
                },
            )
            inserted += 1
            pos_cursor += 1

        if str(scripts[0].get("speaker", "")).strip() != NARRATION_SPEAKER:
            scripts.insert(
                0,
                {
                    "id": "",
                    "speaker": NARRATION_SPEAKER,
                    "text": candidates[0],
                    "character_image": None,
                    "effect": "typewriter",
                    "speed": DEFAULT_TYPEWRITER_SPEED,
                },
            )
            candidates.rotate(-1)

    return result


def normalize_and_repair_script(
    data: dict[str, Any],
    speaker_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    aliases = speaker_aliases or {"我": "盲眼法医"}
    result = copy.deepcopy(data)

    for sb in result.get("storyboards", []):
        scripts = sb.get("scripts", [])
        repaired: list[dict[str, Any]] = []

        for sc in scripts:
            speaker = str(sc.get("speaker", "")).strip()
            speaker = aliases.get(speaker, speaker)
            text = str(sc.get("text", "")).strip()
            parts = _chunk_text(text, 80)
            for part in parts:
                item = {
                    "id": "",
                    "speaker": speaker,
                    "text": part,
                    "character_image": sc.get("character_image"),
                    "effect": "typewriter",
                    "speed": DEFAULT_TYPEWRITER_SPEED,
                }
                if speaker == NARRATION_SPEAKER:
                    item["character_image"] = None
                repaired.append(item)

        sb["scripts"] = repaired

    _reindex_segment_ids(result)
    rebuild_asset_manifest(result)
    return result


def _reindex_segment_ids(data: dict[str, Any]) -> None:
    sid = 1
    for sb in data.get("storyboards", []):
        for sc in sb.get("scripts", []):
            sc["id"] = f"s{sid}"
            sid += 1


def rebuild_asset_manifest(data: dict[str, Any]) -> None:
    manifest: list[dict[str, Any]] = []
    for sb in data.get("storyboards", []):
        bg = ((sb.get("background") or {}).get("image"))
        for sc in sb.get("scripts", []):
            manifest.append(
                {
                    "segment_id": sc.get("id"),
                    "background_image": bg,
                    "character_image": sc.get("character_image"),
                }
            )

    shared = data.setdefault("shared", {})
    shared["asset_manifest"] = manifest
    pipeline_state = shared.setdefault("pipeline_state", {})
    pipeline_state["asset_manifest_count"] = len(manifest)
