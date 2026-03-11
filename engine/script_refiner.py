from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.script_quality import (
    QualityReport,
    analyze_script_quality,
    enrich_narration_with_novel,
    normalize_and_repair_script,
    rebuild_asset_manifest,
)


@dataclass
class RefinementRound:
    round_index: int
    narration_ratio: float
    script_count: int
    issue_count: int


@dataclass
class RefinementResult:
    output: dict[str, Any]
    rounds: list[RefinementRound]
    final_report: QualityReport


def refine_script_until_pass(
    script_data: dict[str, Any],
    novel_text: str,
    min_narration_ratio: float = 0.40,
    max_rounds: int = 3,
) -> RefinementResult:
    current = normalize_and_repair_script(script_data)
    rebuild_asset_manifest(current)

    history: list[RefinementRound] = []

    for round_index in range(1, max_rounds + 1):
        report = analyze_script_quality(current, min_narration_ratio=min_narration_ratio)
        history.append(
            RefinementRound(
                round_index=round_index,
                narration_ratio=report.stats.narration_ratio,
                script_count=report.stats.script_count,
                issue_count=len(report.issues),
            )
        )

        if report.passed and report.stats.narration_ratio >= min_narration_ratio:
            return RefinementResult(current, history, report)

        # 单轮策略：先补旁白，再结构修复。
        enriched = enrich_narration_with_novel(current, novel_text, target_ratio=min_narration_ratio)
        current = normalize_and_repair_script(enriched)
        rebuild_asset_manifest(current)

    final = analyze_script_quality(current, min_narration_ratio=min_narration_ratio)
    return RefinementResult(current, history, final)
