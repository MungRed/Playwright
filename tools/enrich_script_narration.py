import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.script_quality import (
    analyze_script_quality,
    enrich_narration_with_novel,
    load_json,
    normalize_and_repair_script,
    rebuild_asset_manifest,
    save_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich storyboard narration from novel text")
    parser.add_argument("script_path", help="Path to script.json")
    parser.add_argument("novel_path", help="Path to novel_full.md/txt")
    parser.add_argument("--target-ratio", type=float, default=0.40)
    parser.add_argument("--in-place", action="store_true", help="Write changes back to script_path")
    args = parser.parse_args()

    script_path = Path(args.script_path)
    novel_path = Path(args.novel_path)
    data = load_json(script_path)
    novel_text = novel_path.read_text(encoding="utf-8")

    before = analyze_script_quality(data, min_narration_ratio=args.target_ratio)
    enriched = enrich_narration_with_novel(data, novel_text, target_ratio=args.target_ratio)
    repaired = normalize_and_repair_script(enriched)
    rebuild_asset_manifest(repaired)

    shared = repaired.setdefault("shared", {})
    ps = shared.setdefault("pipeline_state", {})
    ps["stage"] = "module2_completed"
    ps["module2_result"] = "pass_narrative_enriched"
    ps["module3_result"] = "pending_rebind_after_module2"
    ps["updated_at"] = "2026-03-11"

    after = analyze_script_quality(repaired, min_narration_ratio=args.target_ratio)

    print(f"before_ratio={before.stats.narration_ratio:.3f}")
    print(f"after_ratio={after.stats.narration_ratio:.3f}")
    print(f"before_scripts={before.stats.script_count}")
    print(f"after_scripts={after.stats.script_count}")

    out = script_path if args.in_place else script_path.with_name(script_path.stem + ".enriched.json")
    save_json(out, repaired)
    print(f"output={out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
