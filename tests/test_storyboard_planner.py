import unittest

from engine.storyboard_planner import build_storyboard_drafts


class StoryboardPlannerTests(unittest.TestCase):
    def test_build_storyboard_drafts(self):
        text = (
            "### 第一章 雨夜回访\n\n"
            "雨丝斜斜划过青石板路，沈砚在旧渡口下车。\n\n"
            "### 第二章 旧案重提\n\n"
            "顾行舟带他去翻卷宗，木屋里炉火噼啪作响。\n\n"
            "### 第三章 暗流涌动\n\n"
            "警局里有人阻拦调查，渡口地皮交易浮出水面。\n\n"
            "### 第四章 魏伯的秘密\n\n"
            "魏伯交出账本线索，暗河入口终于被说破。\n\n"
            "### 第五章 真相浮现\n\n"
            "清晨薄雾里，三人顺着暗河找到了黑船。\n\n"
            "### 第六章 回灯照岸\n\n"
            "雨夜里，证据公开，渡口的灯重新亮起。"
        )
        drafts = build_storyboard_drafts(text, target_count=6)
        self.assertEqual(len(drafts), 6)
        self.assertEqual(drafts[0].id, "sb1")
        self.assertEqual(drafts[0].title, "第一章 雨夜回访")
        self.assertEqual(drafts[-1].title, "第六章 回灯照岸")
        self.assertEqual(len({d.title for d in drafts}), 6)
        self.assertTrue(all(d.background_image.startswith("assets/") for d in drafts))
        self.assertTrue(all("scene_" in d.background_image for d in drafts))


if __name__ == "__main__":
    unittest.main()
