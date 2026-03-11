import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.storyboard_planner import build_storyboard_drafts


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan storyboard drafts from novel text")
    parser.add_argument("novel_path", help="Path to novel_full.md/txt")
    parser.add_argument("--target-count", type=int, default=6)
    parser.add_argument("--output", help="Optional output json path")
    args = parser.parse_args()

    text = Path(args.novel_path).read_text(encoding="utf-8")
    drafts = build_storyboard_drafts(text, target_count=args.target_count)

    payload = [
        {
            "id": d.id,
            "title": d.title,
            "summary": d.summary,
            "background": {"image": d.background_image},
        }
        for d in drafts
    ]

    out_text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(out_text, encoding="utf-8")
        print(f"output={args.output}")
    else:
        print(out_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
