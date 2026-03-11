from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class StoryboardDraft:
    id: str
    title: str
    summary: str
    background_image: str


CHAPTER_HEADING_RE = re.compile(r"^(?:###\s*)?(第[一二三四五六七八九十百0-9]+章)\s+(.+?)\s*$")


def _split_paragraphs(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    return paragraphs


def _split_chapters(text: str) -> list[tuple[str, str]]:
    lines = text.replace("\r\n", "\n").split("\n")
    chapters: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        match = CHAPTER_HEADING_RE.match(stripped)
        if match:
            if current_title:
                chapters.append((current_title, current_lines[:]))
            current_title = f"{match.group(1)} {match.group(2).strip()}"
            current_lines = []
            continue

        if current_title:
            current_lines.append(line)

    if current_title:
        chapters.append((current_title, current_lines[:]))

    normalized: list[tuple[str, str]] = []
    for title, body_lines in chapters:
        body = "\n".join(body_lines).strip()
        if body:
            normalized.append((title, body))
    return normalized


def _score_paragraph(paragraph: str) -> int:
    score = 0
    if any(k in paragraph for k in ["雨", "夜", "清晨", "黄昏", "黎明", "暮色"]):
        score += 2
    if any(k in paragraph for k in ["突然", "就在这时", "转折", "发现", "揭示", "真相"]):
        score += 2
    if len(paragraph) >= 120:
        score += 1
    return score


def _pick_title(paragraph: str, fallback: str) -> str:
    first_line = paragraph.splitlines()[0].strip() if paragraph else ""
    if first_line and len(first_line) <= 24:
        return first_line
    return fallback


def _infer_scene_tags(text: str) -> list[str]:
    tags: list[str] = []
    tag_rules = [
        ("rain", ["雨", "雨夜", "雨幕"]),
        ("night", ["夜", "深夜", "夜色"]),
        ("morning", ["清晨", "晨雾", "黎明", "薄雾"]),
        ("dock", ["渡口", "栈桥", "河岸", "码头"]),
        ("boat", ["船", "渡船", "船舱", "暗河"]),
        ("archive", ["警局", "档案室", "卷宗", "书店"]),
        ("interior", ["木屋", "小屋", "室内", "炉火"]),
        ("reveal", ["真相", "证据", "账本", "调查", "公开"]),
    ]
    for tag, keywords in tag_rules:
        if any(keyword in text for keyword in keywords):
            tags.append(tag)

    if not tags:
        tags.append("story")
    if len(tags) == 1:
        tags.append("scene")
    return tags[:3]


def _background_for_text(text: str, index: int) -> str:
    slug = "_".join(_infer_scene_tags(text))
    return f"assets/scene_{index}_{slug}.png"


def _chapter_summary(body: str) -> str:
    paragraphs = _split_paragraphs(body)
    if not paragraphs:
        return ""

    selected = paragraphs[0]
    if len(selected) < 50 and len(paragraphs) > 1:
        selected += paragraphs[1]
    summary = re.sub(r"\s+", "", selected)
    return summary[:100]


def build_storyboard_drafts(novel_text: str, target_count: int = 6) -> list[StoryboardDraft]:
    chapters = _split_chapters(novel_text)
    if chapters:
        drafts: list[StoryboardDraft] = []
        for i, (title, body) in enumerate(chapters[: max(1, target_count)], start=1):
            drafts.append(
                StoryboardDraft(
                    id=f"sb{i}",
                    title=title,
                    summary=_chapter_summary(body),
                    background_image=_background_for_text(title + "\n" + body, i),
                )
            )
        return drafts

    paragraphs = _split_paragraphs(novel_text)
    if not paragraphs:
        return []

    scored = [(idx, _score_paragraph(p), p) for idx, p in enumerate(paragraphs)]
    scored.sort(key=lambda x: (x[1], len(x[2])), reverse=True)

    selected = sorted(scored[: max(1, min(target_count, len(scored)))], key=lambda x: x[0])
    drafts: list[StoryboardDraft] = []

    for i, (_, _, paragraph) in enumerate(selected, start=1):
        fallback = f"分镜{i}"
        title = _pick_title(paragraph, fallback)
        bg = _background_for_text(paragraph, i)
        summary = re.sub(r"\s+", "", paragraph)
        if len(summary) > 100:
            summary = summary[:100]

        drafts.append(
            StoryboardDraft(
                id=f"sb{i}",
                title=title,
                summary=summary,
                background_image=bg,
            )
        )

    return drafts
