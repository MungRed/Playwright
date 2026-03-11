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

    def test_refine_until_pass_fixes_storyboard_ratio(self):
        data = {
            "storyboards": [
                {
                    "id": "sb1",
                    "title": "测试一",
                    "background": {"image": "assets/a.png"},
                    "scripts": [
                        {"id": "s1", "speaker": "旁白", "text": "雨夜里木门轻响。", "character_image": None},
                        {"id": "s2", "speaker": "甲", "text": "先进去看看。", "character_image": "x"},
                    ],
                },
                {
                    "id": "sb2",
                    "title": "测试二",
                    "background": {"image": "assets/b.png"},
                    "scripts": [
                        {"id": "s3", "speaker": "乙", "text": "都准备好了。", "character_image": "y"},
                        {"id": "s4", "speaker": "丙", "text": "马上动手。", "character_image": "z"},
                        {"id": "s5", "speaker": "乙", "text": "别留下痕迹。", "character_image": "y"},
                    ],
                },
            ]
        }
        novel = "雨水顺着屋檐滴落。空气里有潮湿的铁锈味。渡口空空荡荡。"
        result = refine_script_until_pass(data, novel, min_narration_ratio=0.4, max_rounds=3)
        issue_codes = {issue.code for issue in result.final_report.issues}
        self.assertNotIn("SB_NARRATION_RATIO_LOW", issue_codes)


if __name__ == "__main__":
    unittest.main()
