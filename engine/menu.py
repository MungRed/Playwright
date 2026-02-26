"""主菜单界面"""

import tkinter as tk
import json
import os
import glob

from engine.config import (
    SCRIPTS_DIR,
    BG_MENU, BG_CARD, BG_HOVER,
    FG_MAIN, FG_DIM, FG_HINT,
)


class MainMenuFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game):
        super().__init__(parent, bg=BG_MENU)
        self.pack(fill=tk.BOTH, expand=True)
        self.game = game

        tk.Label(self, text="文字冒险游戏",
                 font=("Microsoft YaHei", 32, "bold"),
                 fg=FG_MAIN, bg=BG_MENU).pack(pady=(70, 6))
        tk.Label(self, text="选择你的冒险",
                 font=("Microsoft YaHei", 13),
                 fg=FG_HINT, bg=BG_MENU).pack(pady=(0, 40))

        # 分割线
        tk.Frame(self, bg=BG_CARD, height=1).pack(fill=tk.X, padx=120, pady=(0, 20))

        scripts = self._load_scripts()
        if scripts:
            for s in scripts:
                self._make_card(s)
        else:
            tk.Label(self,
                     text="未找到游戏脚本\n请在 scripts/ 目录下放置 .json 文件",
                     font=("Microsoft YaHei", 11),
                     fg=FG_DIM, bg=BG_MENU).pack(pady=20)

        tk.Button(self, text="退 出",
                  font=("Microsoft YaHei", 11),
                  fg=FG_HINT, bg=BG_CARD,
                  activeforeground=FG_MAIN, activebackground=BG_HOVER,
                  relief=tk.FLAT, padx=24, pady=7,
                  cursor="hand2",
                  command=parent.quit).pack(pady=(30, 0))

    # ── 扫描脚本目录 ──
    def _load_scripts(self) -> list[dict]:
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        result = []
        for path in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "path":        path,
                    "title":       data.get("title",       os.path.basename(path)),
                    "description": data.get("description", ""),
                })
            except Exception:
                pass
        return result

    # ── 生成游戏卡片 ──
    def _make_card(self, script: dict):
        card = tk.Frame(self, bg=BG_CARD, padx=18, pady=10, cursor="hand2")
        card.pack(pady=6, padx=120, fill=tk.X)

        tk.Label(card, text=script["title"],
                 font=("Microsoft YaHei", 13, "bold"),
                 fg=FG_MAIN, bg=BG_CARD, anchor="w").pack(fill=tk.X)

        if script["description"]:
            tk.Label(card, text=script["description"],
                     font=("Microsoft YaHei", 10),
                     fg=FG_HINT, bg=BG_CARD, anchor="w").pack(fill=tk.X)

        path = script["path"]

        def on_click(_=None):
            self.game.start_game(path)

        def on_enter(_=None):
            card.config(bg=BG_HOVER)
            for w in card.winfo_children():
                w.config(bg=BG_HOVER)

        def on_leave(_=None):
            card.config(bg=BG_CARD)
            for w in card.winfo_children():
                w.config(bg=BG_CARD)

        for w in [card] + list(card.winfo_children()):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)
