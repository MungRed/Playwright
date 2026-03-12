from __future__ import annotations

import copy
import json
import math
import re
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

NARRATION_SPEAKER = "旁白"
DEFAULT_TYPEWRITER_SPEED = 55

CHAPTER_HEADING_LINE_RE = re.compile(r"^\s*(?:#{1,6}\s*)?第[一二三四五六七八九十百0-9]+章\s+.+$", re.IGNORECASE)
LEADING_STAGE_DIR_RE = re.compile(r"^\s*(?:（[^）]{1,12}）|\([^)]{1,12}\))\s*")


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


def _strip_leading_chapter_heading(text: str) -> str:
    lines = text.splitlines()
    while lines and CHAPTER_HEADING_LINE_RE.match(lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip()


def _normalize_segment_text(speaker: str, text: str) -> str:
    out = (text or "").strip()
    out = _strip_leading_chapter_heading(out)
    if speaker and speaker != NARRATION_SPEAKER:
        out = LEADING_STAGE_DIR_RE.sub("", out, count=1).strip()
    return out


def _calculate_similarity(text1: str, text2: str) -> float:
    """计算两个文本的相似度（简单的字符重叠率）"""
    if not text1 or not text2:
        return 0.0

    # 移除空格和标点进行比较
    clean1 = re.sub(r'[\s，。！？：；、""''（）]', '', text1)
    clean2 = re.sub(r'[\s，。！？：；、""''（）]', '', text2)

    if not clean1 or not clean2:
        return 0.0

    # 计算最长公共子序列长度
    len1, len2 = len(clean1), len(clean2)
    if len1 == 0 or len2 == 0:
        return 0.0

    # 使用滑动窗口计算重叠字符数
    overlap = 0
    window_size = min(len1, len2, 20)  # 限制窗口大小避免性能问题

    for i in range(len1 - window_size + 1):
        substr = clean1[i:i+window_size]
        if substr in clean2:
            overlap += window_size

    # 相似度 = 重叠字符数 / 平均长度
    avg_len = (len1 + len2) / 2
    similarity = overlap / avg_len if avg_len > 0 else 0.0

    return min(similarity, 1.0)  # 限制在 0.0-1.0 之间


def _check_duplicate_text(data: dict[str, Any], threshold: float = 0.85) -> list[QualityIssue]:
    """检测重复或高度相似的段落"""
    issues: list[QualityIssue] = []
    texts: list[tuple[str, str]] = []  # (text, location)

    for sb_idx, sb in enumerate(data.get("storyboards", [])):
        for sc_idx, sc in enumerate(sb.get("scripts", [])):
            text = sc.get("text", "").strip()
            if not text or len(text) < 10:  # 跳过过短文本
                continue

            location = f"storyboards[{sb_idx}].scripts[{sc_idx}]"

            # 与已有文本比较相似度
            for prev_text, prev_loc in texts:
                similarity = _calculate_similarity(text, prev_text)
                if similarity >= threshold:
                    issues.append(QualityIssue(
                        level="error",
                        code="DUPLICATE_TEXT",
                        message=f"文本与 {prev_loc} 高度相似（{similarity:.1%}）",
                        location=location
                    ))
                    break  # 找到一个重复就够了，不需要继续比较

            texts.append((text, location))

    return issues


def analyze_script_quality(data: dict[str, Any], min_narration_ratio: float = 0.50) -> QualityReport:
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
            issues.append(QualityIssue("error", "SB_NOT_START_WITH_NARRATION", "分镜未以旁白开头", sb_loc + ".scripts[0]"))

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

            if len(text) > 100:
                issues.append(QualityIssue("error", "TEXT_TOO_LONG", f"text 长度 {len(text)} > 100（严重超标）", sc_loc))
            elif len(text) > 80:
                issues.append(QualityIssue("warn", "TEXT_TOO_LONG", f"text 长度 {len(text)} > 80", sc_loc))

            if CHAPTER_HEADING_LINE_RE.match(text.strip()):
                issues.append(QualityIssue("warn", "TEXT_CHAPTER_HEADING", "text 疑似章节标题泄漏", sc_loc))

            if speaker and speaker != NARRATION_SPEAKER and LEADING_STAGE_DIR_RE.match(text):
                issues.append(QualityIssue("warn", "DIALOGUE_STAGE_PREFIX", "对话包含前置括号舞台提示", sc_loc))

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
        if sb_ratio < 0.45:
            # 严重不达标（<45%）升级为 error
            issues.append(
                QualityIssue(
                    "error",
                    "SB_NARRATION_RATIO_LOW",
                    f"分镜旁白占比 {sb_ratio:.2f} < 0.45（严重不足）",
                    sb_loc,
                )
            )
        elif sb_ratio < min_narration_ratio:
            issues.append(
                QualityIssue(
                    "warn",
                    "SB_NARRATION_RATIO_LOW",
                    f"分镜旁白占比 {sb_ratio:.2f} < {min_narration_ratio:.2f}",
                    sb_loc,
                )
            )

    ratio = (narr / total) if total else 0.0
    if ratio < 0.45:
        # 严重不达标（<45%）升级为 error
        issues.append(
            QualityIssue(
                "error",
                "GLOBAL_NARRATION_RATIO_LOW",
                f"全局旁白占比 {ratio:.2f} < 0.45（严重不足）",
                "storyboards",
            )
        )
    elif ratio < min_narration_ratio:
        issues.append(
            QualityIssue(
                "warn",
                "GLOBAL_NARRATION_RATIO_LOW",
                f"全局旁白占比 {ratio:.2f} < {min_narration_ratio:.2f}",
                "storyboards",
            )
        )

    # 检测重复文本
    duplicate_issues = _check_duplicate_text(data, threshold=0.85)
    issues.extend(duplicate_issues)

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


def _extract_keywords(text: str) -> list[str]:
    """从文本中提取关键词（简单实现）

    Args:
        text: 输入文本（如分镜标题"第一章 雨夜回访"）

    Returns:
        关键词列表（如["雨", "夜", "回访"]）
    """
    # 移除常见标题前缀
    text = re.sub(r"^第[一二三四五六七八九十百千0-9]+章\s*", "", text).strip()

    # 简单分词：按字符切分（适用于中文）
    # 过滤掉单字且为常见虚词的字符
    stop_words = set("的了在是有和与及之为以")
    keywords = [ch for ch in text if ch not in stop_words and ch.strip()]

    return keywords[:10]  # 最多返回10个关键词


def _filter_candidates_by_theme(
    candidates: deque[str],
    storyboard_title: str,
    max_relevant: int = 50,
) -> deque[str]:
    """根据分镜主题筛选相关旁白候选

    Args:
        candidates: 全部旁白候选池
        storyboard_title: 分镜标题（如"第一章 雨夜回访"）
        max_relevant: 最多保留多少个相关候选

    Returns:
        筛选后的候选池（相关候选在前，其他候选在后）
    """
    if not storyboard_title:
        return candidates

    # 提取主题关键词
    keywords = _extract_keywords(storyboard_title)
    if not keywords:
        return candidates

    # 将候选分为相关和无关两类
    relevant: deque[str] = deque()
    others: deque[str] = deque()

    for text in candidates:
        # 检查候选文本是否包含任一关键词
        if any(kw in text for kw in keywords):
            relevant.append(text)
            if len(relevant) >= max_relevant:
                break  # 相关候选已足够
        else:
            others.append(text)

    # 相关候选在前，其他候选在后（兜底）
    relevant.extend(others)
    return relevant


def enrich_narration_with_novel(
    data: dict[str, Any],
    novel_text: str,
    target_ratio: float = 0.50,
) -> dict[str, Any]:
    result = copy.deepcopy(data)
    candidates = _extract_narration_candidates(novel_text)

    # 收集全剧本已有段落文本，用于重复检测
    existing_texts: list[str] = []
    for sb in result.get("storyboards", []):
        for sc in sb.get("scripts", []):
            text = str(sc.get("text", "")).strip()
            if text:
                existing_texts.append(text)

    for sb in result.get("storyboards", []):
        scripts = sb.get("scripts", [])
        if not isinstance(scripts, list) or not scripts:
            continue

        # 计算当前分镜需要补充的旁白数量
        narr = sum(1 for s in scripts if str(s.get("speaker", "")).strip() == NARRATION_SPEAKER)
        total = len(scripts)
        need = _required_insertions(total, narr, target_ratio)
        if need <= 0:
            continue

        # 【Phase 2.4新增】根据分镜标题筛选主题相关的候选
        sb_title = str(sb.get("title", "")).strip()
        sb_candidates = _filter_candidates_by_theme(copy.deepcopy(candidates), sb_title)

        insert_positions = [i for i, s in enumerate(scripts) if str(s.get("speaker", "")).strip() != NARRATION_SPEAKER]
        if not insert_positions:
            continue

        inserted = 0
        pos_cursor = 0
        max_retries = len(sb_candidates)  # 防止无限循环
        retries = 0

        while inserted < need and retries < max_retries:
            candidate_text = sb_candidates[0]
            sb_candidates.rotate(-1)
            retries += 1

            # 前置重复检测：跳过与已有段落高度相似的候选
            is_duplicate = False
            for existing in existing_texts:
                if _calculate_similarity(candidate_text, existing) >= 0.85:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue  # 跳过重复候选，尝试下一个

            # 插入旁白
            pos = insert_positions[pos_cursor % len(insert_positions)] + inserted
            scripts.insert(
                pos,
                {
                    "id": "",
                    "speaker": NARRATION_SPEAKER,
                    "text": candidate_text,
                    "character_image": None,
                    "effect": "typewriter",
                    "speed": DEFAULT_TYPEWRITER_SPEED,
                },
            )
            existing_texts.append(candidate_text)  # 记录已插入文本
            inserted += 1
            pos_cursor += 1
            retries = 0  # 成功插入后重置重试计数

        if str(scripts[0].get("speaker", "")).strip() != NARRATION_SPEAKER:
            # 为分镜开头补充旁白（同样使用主题筛选）
            first_narration = None
            for _ in range(len(sb_candidates)):
                candidate = sb_candidates[0]
                sb_candidates.rotate(-1)

                is_duplicate = False
                for existing in existing_texts:
                    if _calculate_similarity(candidate, existing) >= 0.85:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    first_narration = candidate
                    break

            if first_narration:
                scripts.insert(
                    0,
                    {
                        "id": "",
                        "speaker": NARRATION_SPEAKER,
                        "text": first_narration,
                        "character_image": None,
                        "effect": "typewriter",
                        "speed": DEFAULT_TYPEWRITER_SPEED,
                    },
                )
                existing_texts.append(first_narration)

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
            text = _normalize_segment_text(speaker, str(sc.get("text", "")))
            if not text:
                continue
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

    _reindex_segment_ids(result, preserve_existing=True)
    rebuild_asset_manifest(result)
    return result


def _reindex_segment_ids(data: dict[str, Any], preserve_existing: bool = True) -> None:
    """重新编号段落ID，可选保留已有ID

    Args:
        data: 剧本数据
        preserve_existing: 是否保留已有ID（默认True）
                          - True: 只为缺失ID的段落分配新ID，已有ID保持不变
                          - False: 全部重新编号
    """
    if preserve_existing:
        # 收集已存在的ID
        existing_ids: set[int] = set()
        for sb in data.get("storyboards", []):
            for sc in sb.get("scripts", []):
                sid_str = str(sc.get("id", "")).strip()
                if sid_str and sid_str.startswith("s"):
                    try:
                        existing_ids.add(int(sid_str[1:]))
                    except ValueError:
                        pass  # 忽略无效ID

        # 从最大ID+1开始分配新ID
        next_id = max(existing_ids, default=0) + 1
    else:
        next_id = 1

    # 只为缺失ID的段落分配新ID
    for sb in data.get("storyboards", []):
        for sc in sb.get("scripts", []):
            current_id = str(sc.get("id", "")).strip()
            if not current_id or current_id == "":
                sc["id"] = f"s{next_id}"
                next_id += 1
            elif not preserve_existing:
                # 强制重新编号模式
                sc["id"] = f"s{next_id}"
                next_id += 1


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
