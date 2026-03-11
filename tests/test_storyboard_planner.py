import unittest

from engine.storyboard_planner import build_storyboard_drafts


class StoryboardPlannerTests(unittest.TestCase):
    def test_build_storyboard_drafts(self):
        text = (
            "雨丝斜斜划过青石板路，算命摊铜钱轻响。\n\n"
            "白裙女孩抱着牛皮纸袋求助。\n\n"
            "警笛由远及近，便衣按倒中年男人。\n\n"
            "暮色里老太太拄拐靠近，袖口暗红。\n\n"
            "清晨拆迁墙后发现女尸。\n\n"
            "证物室里揭开真相，阳光刺破云层。"
        )
        drafts = build_storyboard_drafts(text, target_count=6)
        self.assertEqual(len(drafts), 6)
        self.assertEqual(drafts[0].id, "sb1")
        self.assertTrue(all(d.background_image.startswith("assets/") for d in drafts))


if __name__ == "__main__":
    unittest.main()
