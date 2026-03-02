"""游戏主界面：负责加载脚本、逐段展示剧情、处理用户交互"""

import json
import os
import tkinter as tk

from engine.background_controller import BackgroundController
from engine.character_panel import CharacterPanel
from engine.config import BG_DARK, FG_DIM, FG_HINT, FG_MAIN
from engine.effects import EFFECTS, EFFECT_SKIP_COLOR
from engine.sidebar_tabs import ReaderSidebarTabs
from engine.text_render import create_outlined_text, upsert_outlined_text


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
        self._step_texts: list[str] = []
        self._step_index: int = 0
        self._step_seg_id: str = ""

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

    def _unbind_keys(self):
        self.root.unbind("<space>")
        self.root.unbind("<Escape>")
        self.root.unbind("<BackSpace>")

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
                    seg.pop("choices", None)
                    if "next" not in seg and i + 1 < len(raw):
                        seg["next"] = str(i + 1)
                    self.segments[str(i)] = seg
                self.current_id = data.get("start", "0")
            else:
                self.is_linear = False
                self.total_linear = len(raw)
                self.segments = {}
                for k, v in raw.items():
                    seg = dict(v)
                    seg.pop("choices", None)
                    self.segments[str(k)] = seg
                self.current_id = data.get("start", next(iter(self.segments), ""))

            self._title_lbl.config(text=data.get("title", "冒险"))
            self._sync_sidebar("-")
        except Exception as e:
            self.segments = {"0": {"text": f"脚本加载失败：{e}", "effect": "typewriter"}}
            self.current_id = "0"
            self.is_linear = True
            self.total_linear = 1
            self._sync_sidebar("-")

    def _navigate_to(self, seg_id: str):
        self.history.append(self.current_id)
        self.current_id = seg_id
        self._at_ending = False
        self._step_seg_id = ""
        self._step_texts = []
        self._step_index = 0
        self._show_segment()

    def _show_segment(self):
        seg = self.segments.get(self.current_id)
        if seg is None:
            self._show_ending()
            return

        if self._step_seg_id != self.current_id:
            self._step_texts = self._build_step_texts(seg)
            self._step_index = 0
            self._step_seg_id = self.current_id

        text = self._current_step_text
        if not text:
            text = seg.get("text", "")

        effect = seg.get("effect", "typewriter").lower()
        speed = seg.get("speed", 30)

        self._update_progress()
        self._hint_lbl.config(text="点击或按 [空格键] 继续", fg=FG_DIM)
        self.animating = True
        self._at_ending = False

        if self._step_index == 0:
            self._background.configure_for_segment(seg)
            self._background.refresh()
            self._ensure_bg_animation()
            self._character_panel.update_segment(seg)
        else:
            self._background.refresh()

        self._draw_text_backdrop()
        self._canvas.delete("text_layer")
        self._canvas.delete("text_base_layer")
        self._canvas.delete("text_outline")
        self._canvas.delete("anim_text_outline")
        self._canvas.delete("append_anim_outline")
        self._canvas.delete("overlay_layer")

        if self._step_index > 0:
            prev_text = self._step_texts[self._step_index - 1] if self._step_index - 1 >= 0 else ""
            if text.startswith(prev_text):
                append_text = text[len(prev_text):]
            else:
                append_text = text

            if not append_text:
                col = EFFECT_SKIP_COLOR.get(effect, FG_MAIN)
                create_outlined_text(
                    self._canvas,
                    self._cx, self._cy, text=text,
                    font=("Microsoft YaHei", 18 if effect == "shake" else 16,
                          "bold" if effect == "shake" else "normal"),
                    fill=col, width=self._text_width, justify=tk.LEFT, anchor="nw",
                    tags=("text_layer",),
                )
                self._on_anim_done(seg)
                return

            col = EFFECT_SKIP_COLOR.get(effect, FG_MAIN)
            base_font = ("Microsoft YaHei", 18 if effect == "shake" else 16,
                         "bold" if effect == "shake" else "normal")
            create_outlined_text(
                self._canvas,
                self._cx, self._cy, text=prev_text,
                font=base_font,
                fill=col, width=self._text_width, justify=tk.LEFT, anchor="nw",
                tags=("text_base_layer",),
            )

            self._animate_append_text(text, len(prev_text), effect, speed, seg, base_font)
            return

        fx = EFFECTS.get(effect, EFFECTS["typewriter"])
        fx(self._canvas, text, self._cx, self._cy, self._effect_cw,
           speed, seg, self._on_anim_done, self._set_after)

    def _set_after(self, after_id: str):
        self._after_id = after_id

    def _on_anim_done(self, seg: dict):
        self.animating = False
        self._after_id = None
        self._render_current_text_static()
        self._ensure_bg_animation()
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

    def _show_ending(self):
        self._canvas.delete("text_layer")
        self._canvas.delete("text_base_layer")
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

            text = self._current_step_text or seg.get("text", "")
            eff = seg.get("effect", "typewriter")
            col = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
            create_outlined_text(
                self._canvas,
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

        if self._step_index + 1 < len(self._step_texts):
            self._step_index += 1
            self._show_segment()
            return

        next_id = seg.get("next")
        if next_id is not None:
            self._navigate_to(str(next_id))
        else:
            self._show_ending()

    def _on_back(self, _=None):
        if self.animating or not self.history:
            return
        self._at_ending = False
        self.current_id = self.history.pop()
        self._step_seg_id = ""
        self._step_texts = []
        self._step_index = 0
        self._show_segment()

    def _on_escape(self, _=None):
        if self._after_id:
            self._canvas.after_cancel(self._after_id)
        if self._bg_anim_after:
            self._canvas.after_cancel(self._bg_anim_after)
            self._bg_anim_after = None
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
        self._canvas.delete("text_base_layer")
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

        text = self._current_step_text or seg.get("text", "")
        eff = seg.get("effect", "typewriter")
        col = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
        create_outlined_text(
            self._canvas,
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

    def _draw_text_backdrop(self):
        self._canvas.delete("text_backdrop_layer")

    def _render_current_text_static(self):
        seg = self.segments.get(self.current_id, {})
        text = self._current_step_text or seg.get("text", "")
        eff = seg.get("effect", "typewriter")
        col = EFFECT_SKIP_COLOR.get(eff, FG_MAIN)
        self._canvas.delete("text_base_layer")
        self._canvas.delete("anim_text_outline")
        self._canvas.delete("append_anim_outline")
        upsert_outlined_text(
            self._canvas,
            "text_outline",
            self._cx, self._cy, text=text,
            font=("Microsoft YaHei", 18 if eff == "shake" else 16,
                  "bold" if eff == "shake" else "normal"),
            fill=col, width=self._text_width, justify=tk.LEFT, anchor="nw",
            tags=("text_layer",),
        )

    @property
    def _current_step_text(self) -> str:
        if not self._step_texts:
            return ""
        idx = max(0, min(self._step_index, len(self._step_texts) - 1))
        return self._step_texts[idx]

    def _build_step_texts(self, seg: dict) -> list[str]:
        text = str(seg.get("text", "") or "")

        break_lines = seg.get("display_break_lines")
        if isinstance(break_lines, list):
            raw_lines = text.split("\n")
            if raw_lines:
                valid_points: list[int] = []
                max_line = len(raw_lines)
                for p in break_lines:
                    if isinstance(p, int) and 1 <= p < max_line and p not in valid_points:
                        valid_points.append(p)
                valid_points.sort()
                if valid_points:
                    ends = valid_points + [max_line]
                    return ["\n".join(raw_lines[:end]) for end in ends]

        return [text]

    def _animate_append_text(self, full_text: str, base_len: int, effect: str,
                             speed: int, seg: dict, font_spec: tuple):
        if base_len >= len(full_text):
            self._on_anim_done(seg)
            return

        color = EFFECT_SKIP_COLOR.get(effect, FG_MAIN)
        idx = [base_len]

        def tick():
            upsert_outlined_text(
                self._canvas,
                "append_anim_outline",
                self._cx, self._cy, text=full_text[:idx[0]],
                font=font_spec,
                fill=color, width=self._text_width, justify=tk.LEFT, anchor="nw",
                tags=("text_layer",),
            )

            idx[0] += 1
            if idx[0] <= len(full_text):
                self._set_after(self._canvas.after(speed, tick))
            else:
                self._on_anim_done(seg)

        tick()

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
