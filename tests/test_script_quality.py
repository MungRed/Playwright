import unittest

from engine.script_quality import analyze_script_quality, enrich_narration_with_novel, normalize_and_repair_script


class ScriptQualityTests(unittest.TestCase):
    def test_repair_chunks_long_text_and_sets_narration_image_none(self):
        data = {
            "storyboards": [
                {
                    "id": "sb1",
                    "background": {"image": "assets/bg.png"},
                    "scripts": [
                        {
                            "id": "s1",
                            "speaker": "旁白",
                            "text": "a" * 120,
                            "character_image": "assets/should_not_exist.png",
                            "effect": "typewriter",
                            "speed": 10,
                        }
                    ],
                }
            ]
        }
        repaired = normalize_and_repair_script(data)
        scripts = repaired["storyboards"][0]["scripts"]
        self.assertGreaterEqual(len(scripts), 2)
        self.assertTrue(all(len(s["text"]) <= 80 for s in scripts))
        self.assertTrue(all(s["character_image"] is None for s in scripts))
        self.assertTrue(all(s["speed"] == 55 for s in scripts))

    def test_enrich_narration_increases_ratio(self):
        data = {
            "storyboards": [
                {
                    "id": "sb1",
                    "background": {"image": "assets/bg.png"},
                    "scripts": [
                        {"id": "s1", "speaker": "盲眼法医", "text": "问什么？", "character_image": "a"},
                        {"id": "s2", "speaker": "中年男人", "text": "我老婆要离婚", "character_image": "b"},
                        {"id": "s3", "speaker": "中年男人", "text": "您怎么知道", "character_image": "b"},
                    ],
                }
            ]
        }
        before = analyze_script_quality(data, min_narration_ratio=0.4)
        enriched = enrich_narration_with_novel(data, "雨丝划过青石板，铜钱轻撞。", target_ratio=0.4)
        after = analyze_script_quality(enriched, min_narration_ratio=0.4)
        self.assertLess(before.stats.narration_ratio, after.stats.narration_ratio)


if __name__ == "__main__":
    unittest.main()
