"""游戏主界面：负责加载脚本、逐段展示剧情、处理用户交互"""

import tkinter as tk
import json

from engine.config import (
    BG_DARK, BG_CARD, BG_HOVER,
    FG_MAIN, FG_DIM, FG_HINT, ACCENT,
)
from engine.effects import EFFECTS, EFFECT_SKIP_COLOR


class GameFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game, script_path: str):
        super().__init__(parent, bg=BG_DARK)
        self.pack(fill=tk.BOTH, expand=True)
        self.game        = game
        self.root        = parent
        self.script_path = script_path

        # 状态
        self.segments:    dict[str, dict] = {}
        self.current_id:  str             = ""
        self.history:     list[str]       = []   # 用于 BackSpace 回退
        self.is_linear:   bool            = True
        self.total_linear: int            = 0
        self.animating:   bool            = False
        self._at_ending:  bool            = False   # 是否处于结局画面
        self._after_id:   str | None      = None
        self._choice_btns: list[tk.Frame] = []

        self._build_ui()
        self._load_script()
        self.root.after(50, self._show_segment)
        self._bind_keys()

    # ─────────────────────────── UI 构建 ───────────────────────────
    def _build_ui(self):
        # 顶栏
        top = tk.Frame(self, bg=BG_DARK)
        top.pack(fill=tk.X, padx=20, pady=(10, 0))

        self._title_lbl = tk.Label(top, text="",
                                   font=("Microsoft YaHei", 10),
                                   fg=FG_DIM, bg=BG_DARK)
        self._title_lbl.pack(side=tk.LEFT)

        back = tk.Label(top, text="← 返回主菜单 [ESC]",
                        font=("Microsoft YaHei", 9),
                        fg=FG_DIM, bg=BG_DARK, cursor="hand2")
        back.pack(side=tk.RIGHT)
        back.bind("<Button-1>", self._on_escape)

        tk.Frame(self, bg=BG_CARD, height=1).pack(fill=tk.X, padx=20, pady=(6, 0))

        # 进度条
        prog_bg = tk.Frame(self, bg="#1a1a33", height=3)
        prog_bg.pack(fill=tk.X, padx=20, pady=(2, 0))
        self._prog_bar    = tk.Frame(prog_bg, bg=ACCENT, height=3)
        self._prog_bar.place(x=0, y=0, relheight=1, width=0)
        self._prog_bg_ref = prog_bg

        # 文字画布（左键点击推进）
        self._canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0,
                                 cursor="hand2")
        self._canvas.pack(expand=True, fill=tk.BOTH, padx=50, pady=(20, 0))
        self._canvas.bind("<Button-1>", self._on_advance)

        # 选项区域
        self._choices_frame = tk.Frame(self, bg=BG_DARK)
        self._choices_frame.pack(fill=tk.X, padx=60, pady=(8, 0))

        # 底栏
        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.pack(fill=tk.X, pady=(4, 12))

        self._hint_lbl = tk.Label(bottom, text="点击或按 [空格键] 继续",
                                  font=("Microsoft YaHei", 10),
                                  fg=FG_DIM, bg=BG_DARK)
        self._hint_lbl.pack(side=tk.LEFT, padx=25)

        self._idx_lbl = tk.Label(bottom, text="",
                                 font=("Microsoft YaHei", 9),
                                 fg=FG_DIM, bg=BG_DARK)
        self._idx_lbl.pack(side=tk.RIGHT, padx=25)

    # ─────────────────────────── 键位绑定 ───────────────────────────
    def _bind_keys(self):
        self.root.bind("<space>",     self._on_advance)
        self.root.bind("<Escape>",    self._on_escape)
        self.root.bind("<BackSpace>", self._on_back)
        for i in range(1, 10):
            self.root.bind(str(i), lambda e, n=i: self._on_number_key(n))

    def _unbind_keys(self):
        self.root.unbind("<space>")
        self.root.unbind("<Escape>")
        self.root.unbind("<BackSpace>")
        for i in range(1, 10):
            self.root.unbind(str(i))

    # ─────────────────────────── 脚本加载 ───────────────────────────
    def _load_script(self):
        """兼容数组（线性）和字典（分支）两种格式"""
        try:
            with open(self.script_path, encoding="utf-8") as f:
                data = json.load(f)

            raw = data.get("segments", [])

            if isinstance(raw, list):
                # 数组格式：自动添加 next 链
                self.is_linear    = True
                self.total_linear = len(raw)
                self.segments     = {}
                for i, seg in enumerate(raw):
                    seg = dict(seg)
                    if "next" not in seg and "choices" not in seg and i + 1 < len(raw):
                        seg["next"] = str(i + 1)
                    self.segments[str(i)] = seg
                self.current_id = data.get("start", "0")
            else:
                # 字典格式：支持任意跳转
                self.is_linear    = False
                self.total_linear = len(raw)
                self.segments     = {str(k): v for k, v in raw.items()}
                self.current_id   = data.get("start", next(iter(self.segments), ""))

            self._title_lbl.config(text=data.get("title", "冒险"))

        except Exception as e:
            self.segments     = {"0": {"text": f"脚本加载失败：{e}", "effect": "fadein"}}
            self.current_id   = "0"
            self.is_linear    = True
            self.total_linear = 1

    # ─────────────────────────── 段落展示 ───────────────────────────
    def _navigate_to(self, seg_id: str):
        """跳转到指定段落并记录历史"""
        self.history.append(self.current_id)
        self.current_id = seg_id
        self._at_ending  = False
        self._hide_choices()
        self._show_segment()

    def _show_segment(self):
        seg = self.segments.get(self.current_id)
        if seg is None:
            self._show_ending()
            return

        text   = seg.get("text",   "")
        effect = seg.get("effect", "fadein").lower()
        speed  = seg.get("speed",  30)

        self._update_progress()
        self._hint_lbl.config(text="点击或按 [空格键] 继续", fg=FG_DIM)
        self.animating   = True
        self._at_ending  = False
        self._canvas.delete("all")
        self._hide_choices()

        fx = EFFECTS.get(effect, EFFECTS["fadein"])
        fx(self._canvas, text, self._cx, self._cy, self._cw,
           speed, seg, self._on_anim_done, self._set_after)

    def _update_progress(self):
        self.root.update_idletasks()
        total_w = self._prog_bg_ref.winfo_width()

        if self.is_linear:
            try:
                idx      = int(self.current_id)
                progress = (idx + 1) / max(self.total_linear, 1)
                self._idx_lbl.config(text=f"{idx + 1} / {self.total_linear}")
            except ValueError:
                progress = 0
                self._idx_lbl.config(text="")
        else:
            visited  = len(self.history) + 1
            progress = min(visited / max(self.total_linear, 1), 1.0)
            self._idx_lbl.config(text=f"已探索 {visited} 段")

        self._prog_bar.place(x=0, y=0, relheight=1,
                             width=max(2, int(total_w * progress)))

    def _set_after(self, after_id: str):
        self._after_id = after_id

    def _on_anim_done(self, seg: dict):
        self.animating = False
        self._after_id = None
        choices = seg.get("choices", [])
        if choices:
            self._show_choices(choices)
            self._hint_lbl.config(text="请选择……", fg=FG_HINT)
        else:
            self._hint_lbl.config(fg=FG_HINT)

    # ─────────────────────────── 选项 UI ───────────────────────────
    def _show_choices(self, choices: list[dict]):
        self._hide_choices()
        for i, choice in enumerate(choices):
            label_text = f"[{i + 1}]  {choice.get('label', '')}"
            btn = tk.Frame(self._choices_frame, bg=BG_CARD, cursor="hand2")
            btn.pack(fill=tk.X, pady=3)

            lbl = tk.Label(btn, text=label_text,
                           font=("Microsoft YaHei", 11),
                           fg=FG_MAIN, bg=BG_CARD,
                           anchor="w", padx=18, pady=8)
            lbl.pack(fill=tk.X)

            next_id = choice.get("next", "")

            def make_click(nid):
                def handler(_=None):
                    if not self.animating:
                        self._navigate_to(nid)
                return handler

            def make_hover(frame, label, enter: bool):
                def handler(_=None):
                    col = BG_HOVER if enter else BG_CARD
                    frame.config(bg=col)
                    label.config(bg=col)
                return handler

            click = make_click(next_id)
            for w in (btn, lbl):
                w.bind("<Button-1>", click)
                w.bind("<Enter>",    make_hover(btn, lbl, True))
                w.bind("<Leave>",    make_hover(btn, lbl, False))

            self._choice_btns.append(btn)

    def _hide_choices(self):
        for w in self._choice_btns:
            w.destroy()
        self._choice_btns.clear()

    # ─────────────────────────── 结局画面 ───────────────────────────
    def _show_ending(self):
        c = self._canvas
        c.delete("all")
        c.create_text(self._cx, self._cy - 28, text="— 终 —",
                      font=("Microsoft YaHei", 26, "bold"), fill="#666688")
        c.create_text(self._cx, self._cy + 28,
                      text="故事结束，感谢你的体验",
                      font=("Microsoft YaHei", 12), fill=FG_DIM)
        hint = "[ESC] 返回主菜单"
        self._hint_lbl.config(text=hint, fg=FG_DIM)
        self._idx_lbl.config(text="")
        self.animating   = False
        self._at_ending  = True

    # ─────────────────────────── 用户交互 ───────────────────────────
    def _on_advance(self, _=None):
        """空格键 / 鼠标左键：跳过动画 或 推进到下一段"""
        seg = self.segments.get(self.current_id, {})

        if self.animating:
            # 取消定时器，直接渲染最终文本
            if self._after_id:
                self._canvas.after_cancel(self._after_id)
                self._after_id = None
            text = seg.get("text", "")
            eff  = seg.get("effect", "fadein")
            col  = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
            self._canvas.delete("all")
            self._canvas.create_text(
                self._cx, self._cy, text=text,
                font=("Microsoft YaHei",
                      18 if eff == "shake" else 16,
                      "bold" if eff == "shake" else "normal"),
                fill=col, width=self._cw - 60, justify=tk.CENTER)
            self._on_anim_done(seg)
            return

        # 结局画面：点击不响应（仅 BackSpace 可回退）
        if self._at_ending:
            return

        # 有选项时不推进（必须点击选项按钮）
        if seg.get("choices"):
            return

        next_id = seg.get("next")
        if next_id is not None:
            self._navigate_to(str(next_id))
        else:
            self._show_ending()

    def _on_number_key(self, n: int):
        """数字键 1-9 快速选择选项"""
        if self.animating:
            return
        choices = self.segments.get(self.current_id, {}).get("choices", [])
        idx     = n - 1
        if 0 <= idx < len(choices):
            next_id = choices[idx].get("next", "")
            if next_id:
                self._navigate_to(str(next_id))

    def _on_back(self, _=None):
        """BackSpace：返回上一段"""
        if self.animating or not self.history:
            return
        self._hide_choices()
        self._at_ending  = False
        self.current_id = self.history.pop()
        self._show_segment()

    def _on_escape(self, _=None):
        """ESC：返回主菜单"""
        if self._after_id:
            self._canvas.after_cancel(self._after_id)
        self._unbind_keys()
        self.game.show_main_menu()

    # ─────────────────────────── 画布尺寸 ───────────────────────────
    @property
    def _cw(self) -> int:
        self.root.update_idletasks()
        return self._canvas.winfo_width() or 800

    @property
    def _ch(self) -> int:
        self.root.update_idletasks()
        return self._canvas.winfo_height() or 440

    @property
    def _cx(self) -> int:
        return self._cw // 2

    @property
    def _cy(self) -> int:
        return self._ch // 2
