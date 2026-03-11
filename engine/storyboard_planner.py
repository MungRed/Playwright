from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class StoryboardDraft:
    id: str
    title: str
    summary: str
    background_image: str


def _split_paragraphs(text: str) -> list[str]:
    raw = text.replace("\r\n", "\n")
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    return paragraphs


def _score_paragraph(paragraph: str) -> int:
    score = 0
    if any(k in paragraph for k in ["雨", "夜", "清晨", "黄昏", "黎明", "暮色"]):
        score += 2
    if any(k in paragraph for k in ["突然", "就在这时", "转折", "发现", "揭示", "真相"]):
        score += 2
    if len(paragraph) >= 120:
        score += 1
    return score


def _pick_titles(paragraph: str, fallback: str) -> str:
    mapping = [
        ("算命", "雨中算命"),
        ("白裙", "白裙求助"),
        ("警笛", "警笛突至"),
        ("老太太", "暗夜线索"),
        ("尸体", "尸体发现"),
        ("真相", "真相浮现"),
    ]
    for kw, title in mapping:
        if kw in paragraph:
            return title
    return fallback


def _background_for_title(title: str) -> str:
    mapper = {
        "雨中算命": "assets/rain_fortune_stall.png",
        "白裙求助": "assets/white_dress_help.png",
        "警笛突至": "assets/siren_capture.png",
        "暗夜线索": "assets/granny_arrival.png",
        "尸体发现": "assets/evidence_confrontation.png",
        "真相浮现": "assets/sunlight_truth.png",
    }
    return mapper.get(title, "assets/rain_fortune_stall.png")


def build_storyboard_drafts(novel_text: str, target_count: int = 6) -> list[StoryboardDraft]:
    paragraphs = _split_paragraphs(novel_text)
    if not paragraphs:
        return []

    scored = [(idx, _score_paragraph(p), p) for idx, p in enumerate(paragraphs)]
    scored.sort(key=lambda x: (x[1], len(x[2])), reverse=True)

    selected = sorted(scored[: max(1, min(target_count, len(scored)))], key=lambda x: x[0])
    drafts: list[StoryboardDraft] = []

    for i, (_, _, paragraph) in enumerate(selected, start=1):
        fallback = f"分镜{i}"
        title = _pick_titles(paragraph, fallback)
        bg = _background_for_title(title)
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
