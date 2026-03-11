import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.script_quality import analyze_script_quality, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Check script.json quality gates")
    parser.add_argument("script_path", help="Path to script.json")
    parser.add_argument("--min-narration-ratio", type=float, default=0.40)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    data = load_json(args.script_path)
    report = analyze_script_quality(data, min_narration_ratio=args.min_narration_ratio)

    if args.as_json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"storyboards={report.stats.storyboard_count}")
        print(f"scripts={report.stats.script_count}")
        print(f"narration_ratio={report.stats.narration_ratio:.3f}")
        print(f"max_text_len={report.stats.max_text_len}")
        for issue in report.issues:
            print(f"[{issue.level}] {issue.code} @ {issue.location}: {issue.message}")

    has_error = any(i.level == "error" for i in report.issues)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
