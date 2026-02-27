"""主菜单界面"""

import tkinter as tk
import json, os, glob

from engine.config import (
    SCRIPTS_DIR,
    BG_DARK, BG_MENU, BG_CARD, BG_HOVER,
    FG_MAIN, FG_DIM, FG_HINT,
)


class MainMenuFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game):
        super().__init__(parent, bg=BG_MENU)
        self.pack(fill=tk.BOTH, expand=True)
        self.game  = game

        tk.Label(self, text="剧本阅读器",
                 font=("Arial Bold", 44),
                 fg=FG_MAIN, bg=BG_MENU).pack(pady=(48, 8))
        tk.Label(self, text="选择要阅读的剧本",
                 font=("Microsoft YaHei", 14),
                 fg=FG_HINT, bg=BG_MENU).pack(pady=(0, 20))

        panel = tk.Frame(self, bg=BG_DARK, bd=0)
        panel.pack(fill=tk.BOTH, expand=False, padx=220, pady=(0, 28))

        tk.Label(panel, text="可用剧本",
                 font=("Microsoft YaHei", 12),
                 fg=FG_HINT, bg=BG_DARK).pack(pady=(14, 8))

        tk.Frame(panel, bg=BG_CARD, height=1).pack(fill=tk.X, padx=30, pady=(0, 6))

        scripts = self._load_scripts()
        if scripts:
            for s in scripts:
                self._make_card(panel, s)
        else:
            tk.Label(panel,
                     text="未找到剧本文件\n请在 scripts/ 目录下放置 .json 文件",
                     font=("Microsoft YaHei", 11),
                     fg=FG_DIM, bg=BG_DARK).pack(pady=16)

        tk.Frame(panel, bg=BG_CARD, height=1).pack(fill=tk.X, padx=30, pady=(6, 0))

        tk.Button(panel, text="退  出",
                  font=("Microsoft YaHei", 10),
                  fg=FG_HINT, bg=BG_CARD,
                  activeforeground=FG_MAIN, activebackground=BG_HOVER,
                  relief=tk.FLAT, padx=20, pady=6,
                  cursor="hand2",
                  command=parent.quit).pack(pady=(10, 16))

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
    def _make_card(self, parent: tk.Frame, script: dict):
        card = tk.Frame(parent, bg=BG_CARD, padx=16, pady=9, cursor="hand2")
        card.pack(pady=5, padx=30, fill=tk.X)

        tk.Label(card, text=script["title"],
                 font=("Microsoft YaHei", 12, "bold"),
                 fg=FG_MAIN, bg=BG_CARD, anchor="w").pack(fill=tk.X)

        if script["description"]:
            tk.Label(card, text=script["description"],
                     font=("Microsoft YaHei", 9),
                     fg=FG_HINT, bg=BG_CARD, anchor="w").pack(fill=tk.X)

        path = script["path"]

        def on_click(_=None):
            self.game.start_game(path)

        def on_enter(_=None):
            card.config(bg=BG_HOVER)
            for w in card.winfo_children():
                if isinstance(w, tk.Label):
                    w.config(bg=BG_HOVER)

        def on_leave(_=None):
            card.config(bg=BG_CARD)
            for w in card.winfo_children():
                if isinstance(w, tk.Label):
                    w.config(bg=BG_CARD)

        for w in [card] + list(card.winfo_children()):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)
