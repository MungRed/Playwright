"""主菜单界面"""

import tkinter as tk
import json, os, glob

from engine.config import (
    SCRIPTS_DIR, COVER_IMG,
    BG_DARK, BG_MENU, BG_CARD, BG_HOVER,
    FG_MAIN, FG_DIM, FG_HINT,
)

try:
    from PIL import Image, ImageTk, ImageDraw
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

_W, _H     = 1280, 720
_PANEL_W   = 760        # 内容面板宽度
_PANEL_TOP = 390        # 面板顶部 y（标题图下方）
_PANEL_BG  = "#0c0c1c"  # 与渐变遮罩末色接近


class MainMenuFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game):
        super().__init__(parent, bg=BG_DARK)
        self.pack(fill=tk.BOTH, expand=True)
        self.game  = game
        self._imgs = []   # 防 GC

        # ── Canvas：全屏底层 ──
        cv = tk.Canvas(self, width=_W, height=_H, bd=0,
                       highlightthickness=0, bg=BG_DARK)
        cv.place(x=0, y=0)

        # ── 背景图 + 从上到下渐深的遮罩（PIL 合成为单张图）──
        if _PIL_OK and os.path.isfile(COVER_IMG):
            try:
                base = (Image.open(COVER_IMG)
                             .resize((_W, _H), Image.LANCZOS)
                             .convert("RGBA"))
                ov = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
                d  = ImageDraw.Draw(ov)
                for y in range(_H):
                    t = max(0.0, (y / _H - 0.18) / 0.82)
                    a = int(min(t ** 1.1, 1.0) * 218)
                    d.line([(0, y), (_W, y)], fill=(8, 8, 20, a))
                base.alpha_composite(ov)
                tk_bg = ImageTk.PhotoImage(base)
                self._imgs.append(tk_bg)
                cv.create_image(0, 0, anchor="nw", image=tk_bg)
            except Exception:
                # 无图时退化为纯色
                pass
        else:
            # 无封面图：纯色背景 + 文字标题
            cv.create_text(_W // 2, 160, text="Playwright",
                           font=("Arial Bold", 64),
                           fill="#dde2ff")
            cv.create_text(_W // 2, 240, text="文字冒险游戏引擎",
                           font=("Microsoft YaHei", 22),
                           fill="#7788cc")

        # ── 内容面板，通过 create_window 悬浮在图片上 ──
        panel = tk.Frame(cv, bg=_PANEL_BG, bd=0)
        cv.create_window(_W // 2, _PANEL_TOP, anchor="n",
                         window=panel, width=_PANEL_W)

        tk.Label(panel, text="选 择 你 的 冒 险",
                 font=("Microsoft YaHei", 12),
                 fg=FG_HINT, bg=_PANEL_BG).pack(pady=(14, 8))

        tk.Frame(panel, bg=BG_CARD, height=1).pack(fill=tk.X, padx=30, pady=(0, 6))

        scripts = self._load_scripts()
        if scripts:
            for s in scripts:
                self._make_card(panel, s)
        else:
            tk.Label(panel,
                     text="未找到游戏脚本\n请在 scripts/ 目录下放置 .json 文件",
                     font=("Microsoft YaHei", 11),
                     fg=FG_DIM, bg=_PANEL_BG).pack(pady=16)

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
                w.config(bg=BG_HOVER)

        def on_leave(_=None):
            card.config(bg=BG_CARD)
            for w in card.winfo_children():
                w.config(bg=BG_CARD)

        for w in [card] + list(card.winfo_children()):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>",    on_enter)
            w.bind("<Leave>",    on_leave)
