"""游戏主界面：负责加载脚本、逐段展示剧情、处理用户交互"""

import json
import os
import tkinter as tk

from engine.background_controller import BackgroundController
from engine.character_panel import CharacterPanel
from engine.config import BG_CARD, BG_DARK, BG_HOVER, FG_DIM, FG_HINT, FG_MAIN
from engine.effects import EFFECTS, EFFECT_SKIP_COLOR
from engine.sidebar_tabs import ReaderSidebarTabs


class GameFrame(tk.Frame):
    CENTER_WIDTH = 1280
    CENTER_HEIGHT = 720
    LEFT_SIDEBAR_WIDTH = 220
    RIGHT_SIDEBAR_WIDTH = 240

    TEXT_PANEL_MARGIN_X = 34
    TEXT_PANEL_MARGIN_TOP = 20
    TEXT_PANEL_MARGIN_BOTTOM = 26
    TEXT_PANEL_PADDING_X = 24
    TEXT_PANEL_PADDING_Y = 18

    def __init__(self, parent: tk.Tk, game, script_path: str):
        super().__init__(parent, bg=BG_DARK)
        self.pack(fill=tk.BOTH, expand=True)
        self.game = game
        self.root = parent
        self.script_path = script_path

        self.segments: dict[str, dict] = {}
        self.current_id: str = ""
        self.history: list[str] = []
        self.is_linear: bool = True
        self.total_linear: int = 0
        self.animating: bool = False
        self._at_ending: bool = False
        self._after_id: str | None = None
        self._bg_anim_after: str | None = None
        self._choice_btns: list[tk.Frame] = []
        self._choices_visible: bool = False
        self._choices_anim_after: str | None = None
        self._choices_opacity: float = 0.0
        self._choices_base_y: int = -12
        self._choices_hidden_y: int = 18
        self._choices_current_y: int = self._choices_hidden_y

        self._project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self._build_ui()
        self._background = BackgroundController(self._canvas, self._project_root)

        self._load_script()
        self.root.after(50, self._show_segment)
        self._bind_keys()

    def _build_ui(self):
        shell = tk.Frame(self, bg=BG_DARK)
        shell.pack(fill=tk.BOTH, expand=True)

        row = tk.Frame(shell, bg=BG_DARK)
        row.pack(expand=True)

        self._sidebar = ReaderSidebarTabs(row, on_back=self._on_back, on_escape=self._on_escape)
        self._sidebar.configure(width=self.LEFT_SIDEBAR_WIDTH)
        self._sidebar.pack(side=tk.LEFT, fill=tk.Y)

        center = tk.Frame(row, bg=BG_DARK, width=self.CENTER_WIDTH, height=self.CENTER_HEIGHT)
        center.pack(side=tk.LEFT)
        center.pack_propagate(False)

        self._character_panel = CharacterPanel(row, self._project_root, width=self.RIGHT_SIDEBAR_WIDTH)
        self._character_panel.pack(side=tk.LEFT, fill=tk.Y)

        top = tk.Frame(center, bg=BG_DARK)
        top.pack(fill=tk.X, padx=20, pady=(10, 0))

        self._title_lbl = tk.Label(top, text="", font=("Microsoft YaHei", 10), fg=FG_DIM, bg=BG_DARK)
        self._title_lbl.pack(side=tk.LEFT)

        back = tk.Label(top, text="← 返回主菜单 [ESC]", font=("Microsoft YaHei", 9),
                        fg=FG_DIM, bg=BG_DARK, cursor="hand2")
        back.pack(side=tk.RIGHT)
        back.bind("<Button-1>", self._on_escape)

        self._canvas = tk.Canvas(center, bg=BG_DARK, highlightthickness=0, cursor="hand2")
        self._canvas.pack(expand=True, fill=tk.BOTH, padx=50, pady=(20, 0))
        self._canvas.bind("<Button-1>", self._on_advance)
        self._canvas.bind("<Configure>", self._on_canvas_resize)

        self._choices_frame = tk.Frame(center, bg=BG_DARK)
        self._choices_frame.place(in_=self._canvas, relx=0.5, rely=1.0, anchor="s", relwidth=0.92, y=-12)
        self._choices_frame.lift()
        self._choices_frame.place_forget()

        bottom = tk.Frame(center, bg=BG_DARK)
        bottom.pack(fill=tk.X, pady=(4, 12))

        self._hint_lbl = tk.Label(bottom, text="点击或按 [空格键] 继续",
                                  font=("Microsoft YaHei", 10), fg=FG_DIM, bg=BG_DARK)
        self._hint_lbl.pack(side=tk.LEFT, padx=25)

        self._idx_lbl = tk.Label(bottom, text="", font=("Microsoft YaHei", 9), fg=FG_DIM, bg=BG_DARK)
        self._idx_lbl.pack(side=tk.RIGHT, padx=25)

    def _bind_keys(self):
        self.root.bind("<space>", self._on_advance)
        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<BackSpace>", self._on_back)
        for i in range(1, 10):
            self.root.bind(str(i), lambda e, n=i: self._on_number_key(n))

    def _unbind_keys(self):
        self.root.unbind("<space>")
        self.root.unbind("<Escape>")
        self.root.unbind("<BackSpace>")
        for i in range(1, 10):
            self.root.unbind(str(i))

    def _load_script(self):
        try:
            with open(self.script_path, encoding="utf-8") as f:
                data = json.load(f)

            raw = data.get("segments", [])
            if isinstance(raw, list):
                self.is_linear = True
                self.total_linear = len(raw)
                self.segments = {}
                for i, seg in enumerate(raw):
                    seg = dict(seg)
                    if "next" not in seg and "choices" not in seg and i + 1 < len(raw):
                        seg["next"] = str(i + 1)
                    self.segments[str(i)] = seg
                self.current_id = data.get("start", "0")
            else:
                self.is_linear = False
                self.total_linear = len(raw)
                self.segments = {str(k): v for k, v in raw.items()}
                self.current_id = data.get("start", next(iter(self.segments), ""))

            self._title_lbl.config(text=data.get("title", "冒险"))
            self._sync_sidebar("-")
        except Exception as e:
            self.segments = {"0": {"text": f"脚本加载失败：{e}", "effect": "fadein"}}
            self.current_id = "0"
            self.is_linear = True
            self.total_linear = 1
            self._sync_sidebar("-")

    def _navigate_to(self, seg_id: str):
        self.history.append(self.current_id)
        self.current_id = seg_id
        self._at_ending = False
        self._hide_choices(animate=False)
        self._show_segment()

    def _show_segment(self):
        seg = self.segments.get(self.current_id)
        if seg is None:
            self._show_ending()
            return

        text = seg.get("text", "")
        effect = seg.get("effect", "fadein").lower()
        speed = seg.get("speed", 30)

        self._update_progress()
        self._hint_lbl.config(text="点击或按 [空格键] 继续", fg=FG_DIM)
        self.animating = True
        self._at_ending = False

        self._background.configure_for_segment(seg)
        self._background.refresh()
        self._ensure_bg_animation()
        self._character_panel.update_segment(seg)

        self._draw_text_backdrop()
        self._canvas.delete("text_layer")
        self._canvas.delete("overlay_layer")
        self._hide_choices(animate=False)

        fx = EFFECTS.get(effect, EFFECTS["fadein"])
        fx(self._canvas, text, self._cx, self._cy, self._effect_cw,
           speed, seg, self._on_anim_done, self._set_after)

    def _set_after(self, after_id: str):
        self._after_id = after_id

    def _on_anim_done(self, seg: dict):
        self.animating = False
        self._after_id = None
        self._ensure_bg_animation()
        choices = seg.get("choices", [])
        if choices:
            self._show_choices(choices)
            self._hint_lbl.config(text="请选择……", fg=FG_HINT)
        else:
            self._hint_lbl.config(fg=FG_HINT)

    def _update_progress(self):
        if self.is_linear:
            try:
                idx = int(self.current_id)
                progress = (idx + 1) / max(self.total_linear, 1)
                progress_text = f"{idx + 1} / {self.total_linear}（{int(progress * 100)}%）"
            except ValueError:
                progress_text = "-"
        else:
            visited = len(self.history) + 1
            progress = min(visited / max(self.total_linear, 1), 1.0)
            progress_text = f"已探索 {visited} 段（{int(progress * 100)}%）"

        self._idx_lbl.config(text=progress_text)
        self._sync_sidebar(progress_text)

    def _sync_sidebar(self, progress_text: str):
        visited = set(self.history)
        if self.current_id:
            visited.add(self.current_id)
        self._sidebar.update_script_state(progress_text, self.current_id, self.segments, visited)

    def _show_choices(self, choices: list[dict]):
        self._cancel_choices_anim()
        self._clear_choice_buttons()
        self._choices_frame.place(
            in_=self._canvas,
            relx=0.5,
            rely=1.0,
            anchor="s",
            relwidth=0.92,
            y=self._choices_hidden_y,
        )
        self._choices_visible = True
        self._choices_opacity = 0.0
        self._choices_current_y = self._choices_hidden_y
        for i, choice in enumerate(choices):
            label_text = f"[{i + 1}]  {choice.get('label', '')}"
            btn = tk.Frame(self._choices_frame, bg=BG_CARD, cursor="hand2")
            btn.pack(fill=tk.X, pady=3)

            lbl = tk.Label(btn, text=label_text, font=("Microsoft YaHei", 11),
                           fg=FG_MAIN, bg=BG_CARD, anchor="w", padx=18, pady=8)
            lbl.pack(fill=tk.X)

            next_id = choice.get("next", "")

            def make_click(nid):
                def handler(_=None):
                    if not self.animating and self._choices_visible:
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
                w.bind("<Enter>", make_hover(btn, lbl, True))
                w.bind("<Leave>", make_hover(btn, lbl, False))

            self._choice_btns.append(btn)

        self._animate_choices_overlay(show=True)

    def _hide_choices(self, animate: bool = True):
        if not animate:
            self._cancel_choices_anim()
            self._clear_choice_buttons()
            self._choices_frame.place_forget()
            self._choices_visible = False
            self._choices_opacity = 0.0
            self._choices_current_y = self._choices_hidden_y
            self._canvas.delete("choice_overlay_layer")
            return

        if not self._choice_btns and self._choices_opacity <= 0.0:
            self._choices_visible = False
            self._canvas.delete("choice_overlay_layer")
            self._choices_frame.place_forget()
            return

        self._choices_visible = False
        self._animate_choices_overlay(show=False)

    def _clear_choice_buttons(self):
        for w in self._choice_btns:
            w.destroy()
        self._choice_btns.clear()

    def _render_choices_overlay(self):
        self._canvas.delete("choice_overlay_layer")
        if self._choices_opacity <= 0.0:
            return
        self.root.update_idletasks()
        overlay_height = max(72, min(220, self._choices_frame.winfo_reqheight() + 14))
        left = 14
        right = max(left + 40, self._cw - 14)
        bottom = self._ch - 8 + self._choices_current_y - self._choices_base_y
        top = max(8, bottom - overlay_height)
        if self._choices_opacity < 0.34:
            stipple = "gray12"
        elif self._choices_opacity < 0.67:
            stipple = "gray25"
        else:
            stipple = "gray50"
        self._canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill="#000000",
            outline="",
            stipple=stipple,
            tags=("choice_overlay_layer",),
        )
        self._canvas.tag_raise("choice_overlay_layer")

    def _animate_choices_overlay(self, show: bool):
        self._cancel_choices_anim()

        target = 1.0 if show else 0.0
        step = 0.22

        def tick():
            self._choices_anim_after = None

            if target > self._choices_opacity:
                self._choices_opacity = min(target, self._choices_opacity + step)
            else:
                self._choices_opacity = max(target, self._choices_opacity - step)

            y_span = self._choices_hidden_y - self._choices_base_y
            self._choices_current_y = int(self._choices_hidden_y - y_span * self._choices_opacity)

            if self._choices_opacity > 0.0:
                self._choices_frame.place(
                    in_=self._canvas,
                    relx=0.5,
                    rely=1.0,
                    anchor="s",
                    relwidth=0.92,
                    y=self._choices_current_y,
                )

            self._render_choices_overlay()

            if self._choices_opacity != target:
                self._choices_anim_after = self._canvas.after(33, tick)
                return

            if target <= 0.0:
                self._clear_choice_buttons()
                self._choices_frame.place_forget()
                self._canvas.delete("choice_overlay_layer")

        tick()

    def _cancel_choices_anim(self):
        if self._choices_anim_after:
            self._canvas.after_cancel(self._choices_anim_after)
            self._choices_anim_after = None

    def _show_ending(self):
        self._canvas.delete("text_layer")
        self._canvas.delete("overlay_layer")
        self._background.refresh()

        cx = self._cw // 2
        cy = self._ch // 2
        self._canvas.create_text(cx, cy - 28, text="— 终 —",
                                 font=("Microsoft YaHei", 26, "bold"), fill="#666688",
                                 tags=("overlay_layer",))
        self._canvas.create_text(cx, cy + 28, text="故事结束，感谢你的体验",
                                 font=("Microsoft YaHei", 12), fill=FG_DIM,
                                 tags=("overlay_layer",))

        self._hint_lbl.config(text="[ESC] 返回主菜单", fg=FG_DIM)
        self._idx_lbl.config(text="")
        self.animating = False
        self._at_ending = True

    def _on_advance(self, _=None):
        seg = self.segments.get(self.current_id, {})

        if self.animating:
            if self._after_id:
                self._canvas.after_cancel(self._after_id)
                self._after_id = None

            text = seg.get("text", "")
            eff = seg.get("effect", "fadein")
            col = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
            self._canvas.delete("text_layer")
            self._canvas.create_text(
                self._cx, self._cy, text=text,
                font=("Microsoft YaHei", 18 if eff == "shake" else 16,
                      "bold" if eff == "shake" else "normal"),
                fill=col, width=self._text_width, justify=tk.LEFT, anchor="nw",
                tags=("text_layer",),
            )
            self._on_anim_done(seg)
            return

        if self._at_ending:
            return

        if seg.get("choices"):
            return

        next_id = seg.get("next")
        if next_id is not None:
            self._navigate_to(str(next_id))
        else:
            self._show_ending()

    def _on_number_key(self, n: int):
        if self.animating or not self._choices_visible:
            return
        choices = self.segments.get(self.current_id, {}).get("choices", [])
        idx = n - 1
        if 0 <= idx < len(choices):
            next_id = choices[idx].get("next", "")
            if next_id:
                self._navigate_to(str(next_id))

    def _on_back(self, _=None):
        if self.animating or not self.history:
            return
        self._hide_choices(animate=False)
        self._at_ending = False
        self.current_id = self.history.pop()
        self._show_segment()

    def _on_escape(self, _=None):
        if self._after_id:
            self._canvas.after_cancel(self._after_id)
        if self._bg_anim_after:
            self._canvas.after_cancel(self._bg_anim_after)
            self._bg_anim_after = None
        self._cancel_choices_anim()
        self._unbind_keys()
        self.game.show_main_menu()

    def _ensure_bg_animation(self):
        if not self._background.has_active_animation or self._bg_anim_after:
            return

        def tick():
            self._bg_anim_after = None
            self._background.refresh()
            if self._background.has_active_animation:
                self._bg_anim_after = self._canvas.after(33, tick)

        self._bg_anim_after = self._canvas.after(33, tick)

    def _redraw_static_canvas(self):
        seg = self.segments.get(self.current_id)
        self._canvas.delete("text_layer")
        self._canvas.delete("overlay_layer")
        self._background.refresh()
        self._draw_text_backdrop()

        if self._at_ending:
            cx = self._cw // 2
            cy = self._ch // 2
            self._canvas.create_text(cx, cy - 28, text="— 终 —",
                                     font=("Microsoft YaHei", 26, "bold"), fill="#666688",
                                     tags=("overlay_layer",))
            self._canvas.create_text(cx, cy + 28, text="故事结束，感谢你的体验",
                                     font=("Microsoft YaHei", 12), fill=FG_DIM,
                                     tags=("overlay_layer",))
            return

        if not seg:
            return

        text = seg.get("text", "")
        eff = seg.get("effect", "fadein")
        col = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
        self._canvas.create_text(
            self._cx, self._cy, text=text,
            font=("Microsoft YaHei", 18 if eff == "shake" else 16,
                  "bold" if eff == "shake" else "normal"),
            fill=col, width=self._text_width, justify=tk.LEFT, anchor="nw",
            tags=("text_layer",),
        )

    def _on_canvas_resize(self, _=None):
        self._background.on_resize()
        if not self.animating:
            self._redraw_static_canvas()
            self._ensure_bg_animation()
        if self._choices_visible or self._choices_opacity > 0.0:
            self._render_choices_overlay()

    def _draw_text_backdrop(self):
        self._canvas.delete("text_backdrop_layer")
        left = self.TEXT_PANEL_MARGIN_X
        top = self.TEXT_PANEL_MARGIN_TOP
        right = max(left + 60, self._cw - self.TEXT_PANEL_MARGIN_X)
        bottom = max(top + 60, self._ch - self.TEXT_PANEL_MARGIN_BOTTOM)
        self._canvas.create_rectangle(
            left,
            top,
            right,
            bottom,
            fill=BG_DARK,
            outline="",
            tags=("text_backdrop_layer",),
        )
        self._canvas.tag_raise("text_backdrop_layer")


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
        return self.TEXT_PANEL_MARGIN_X + self.TEXT_PANEL_PADDING_X

    @property
    def _cy(self) -> int:
        return self.TEXT_PANEL_MARGIN_TOP + self.TEXT_PANEL_PADDING_Y

    @property
    def _text_width(self) -> int:
        total = self._cw - self.TEXT_PANEL_MARGIN_X * 2 - self.TEXT_PANEL_PADDING_X * 2
        return max(120, total)

    @property
    def _effect_cw(self) -> int:
        return self._text_width + 80
