import unittest

from engine.script_refiner import refine_script_until_pass


class ScriptRefinerTests(unittest.TestCase):
    def test_refine_until_pass_ratio(self):
        data = {
            "storyboards": [
                {
                    "id": "sb1",
                    "title": "测试",
                    "background": {"image": "assets/a.png"},
                    "scripts": [
                        {"id": "s1", "speaker": "盲眼法医", "text": "问什么", "character_image": "x"},
                        {"id": "s2", "speaker": "中年男人", "text": "我来求卦", "character_image": "y"},
                        {"id": "s3", "speaker": "中年男人", "text": "我老婆要离婚", "character_image": "y"},
                    ],
                }
            ]
        }
        novel = "雨丝划过青石板，铜钱在竹筒里轻响。"
        result = refine_script_until_pass(data, novel, min_narration_ratio=0.4, max_rounds=3)
        self.assertGreaterEqual(result.final_report.stats.narration_ratio, 0.4)
        self.assertTrue(result.final_report.passed)


if __name__ == "__main__":
    unittest.main()
