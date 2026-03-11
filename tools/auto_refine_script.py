import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.script_quality import load_json, save_json
from engine.script_refiner import refine_script_until_pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto refine script.json with iterative quality loop")
    parser.add_argument("script_path", help="Path to script.json")
    parser.add_argument("novel_path", help="Path to novel_full.md/txt")
    parser.add_argument("--min-narration-ratio", type=float, default=0.40)
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()

    data = load_json(args.script_path)
    novel = Path(args.novel_path).read_text(encoding="utf-8")

    result = refine_script_until_pass(
        data,
        novel,
        min_narration_ratio=args.min_narration_ratio,
        max_rounds=args.max_rounds,
    )

    for item in result.rounds:
        print(
            f"round={item.round_index} narration_ratio={item.narration_ratio:.3f} "
            f"scripts={item.script_count} issues={item.issue_count}"
        )

    print(f"final_passed={result.final_report.passed}")
    print(f"final_ratio={result.final_report.stats.narration_ratio:.3f}")

    out_path = Path(args.script_path) if args.in_place else Path(args.script_path).with_name("script.refined.json")
    save_json(out_path, result.output)
    print(f"output={out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
