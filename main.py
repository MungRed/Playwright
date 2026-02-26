import tkinter as tk
import json
import os
import glob
import math
import random

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")

BG_DARK   = "#0d0d1a"
BG_MENU   = "#1a1a2e"
BG_CARD   = "#2d2d4e"
BG_HOVER  = "#3d3d6e"
FG_MAIN   = "#d0d0e8"
FG_DIM    = "#555577"
FG_HINT   = "#8888aa"
ACCENT    = "#5566ff"


# ─────────────────────────── 颜色工具 ───────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r, g, b):
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

def lerp_color(c1_hex, c2_hex, t):
    a, b_rgb = hex_to_rgb(c1_hex), hex_to_rgb(c2_hex)
    r = a[0] + (b_rgb[0] - a[0]) * t
    g = a[1] + (b_rgb[1] - a[1]) * t
    b = a[2] + (b_rgb[2] - a[2]) * t
    return rgb_to_hex(r, g, b)


# ─────────────────────────── 主程序 ───────────────────────────
class TextAdventureGame:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("文字冒险游戏")
        self.root.geometry("900x600")
        self.root.configure(bg=BG_MENU)
        self.root.resizable(False, False)
        self._frame: tk.Frame | None = None
        self.show_main_menu()

    def _set_frame(self, frame: tk.Frame):
        if self._frame:
            self._frame.destroy()
        self._frame = frame

    def show_main_menu(self):
        self._set_frame(MainMenuFrame(self.root, self))

    def start_game(self, script_path: str):
        self._set_frame(GameFrame(self.root, self, script_path))


# ─────────────────────────── 主菜单 ───────────────────────────
class MainMenuFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game: TextAdventureGame):
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

    def _load_scripts(self) -> list[dict]:
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        result = []
        for path in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                result.append({
                    "path": path,
                    "title": data.get("title", os.path.basename(path)),
                    "description": data.get("description", ""),
                })
            except Exception:
                pass
        return result

    def _make_card(self, script: dict):
        card = tk.Frame(self, bg=BG_CARD, padx=18, pady=10, cursor="hand2")
        card.pack(pady=6, padx=120, fill=tk.X)

        title_lbl = tk.Label(card, text=script["title"],
                             font=("Microsoft YaHei", 13, "bold"),
                             fg=FG_MAIN, bg=BG_CARD, anchor="w")
        title_lbl.pack(fill=tk.X)

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
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)


# ─────────────────────────── 游戏帧 ───────────────────────────
class GameFrame(tk.Frame):
    def __init__(self, parent: tk.Tk, game: TextAdventureGame, script_path: str):
        super().__init__(parent, bg=BG_DARK)
        self.pack(fill=tk.BOTH, expand=True)
        self.game = game
        self.root = parent
        self.script_path = script_path

        self.segments: list[dict] = []
        self.current_idx = 0
        self.animating = False
        self._after_id: str | None = None

        self._build_ui()
        self._load_script()
        self._show_segment()

        self.root.bind("<space>",  self._on_space)
        self.root.bind("<Escape>", self._on_escape)

    # ── UI 构建 ──
    def _build_ui(self):
        top = tk.Frame(self, bg=BG_DARK)
        top.pack(fill=tk.X, padx=20, pady=(10, 0))

        self._title_lbl = tk.Label(top, text="", font=("Microsoft YaHei", 10),
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
        self._prog_bar = tk.Frame(prog_bg, bg=ACCENT, height=3)
        self._prog_bar.place(x=0, y=0, relheight=1, width=0)
        self._prog_bg_ref = prog_bg  # 保存引用供更新宽度

        # 文字画布
        self._canvas = tk.Canvas(self, bg=BG_DARK, highlightthickness=0)
        self._canvas.pack(expand=True, fill=tk.BOTH, padx=50, pady=(20, 5))

        bottom = tk.Frame(self, bg=BG_DARK)
        bottom.pack(fill=tk.X, pady=(0, 12))

        self._hint_lbl = tk.Label(bottom, text="按 [空格键] 继续",
                                  font=("Microsoft YaHei", 10),
                                  fg=FG_DIM, bg=BG_DARK)
        self._hint_lbl.pack(side=tk.LEFT, padx=25)

        self._idx_lbl = tk.Label(bottom, text="",
                                 font=("Microsoft YaHei", 9),
                                 fg=FG_DIM, bg=BG_DARK)
        self._idx_lbl.pack(side=tk.RIGHT, padx=25)

    # ── 脚本加载 ──
    def _load_script(self):
        try:
            with open(self.script_path, encoding="utf-8") as f:
                data = json.load(f)
            self.segments = data.get("segments", [])
            self._title_lbl.config(text=data.get("title", "冒险"))
        except Exception as e:
            self.segments = [{"text": f"脚本加载失败：{e}", "effect": "fadein"}]

    # ── 展示当前段落 ──
    def _show_segment(self):
        if self.current_idx >= len(self.segments):
            self._show_ending()
            return

        seg   = self.segments[self.current_idx]
        text  = seg.get("text", "")
        effect= seg.get("effect", "fadein").lower()
        speed = seg.get("speed", 30)

        # 进度条
        self.root.update_idletasks()
        total_w = self._prog_bg_ref.winfo_width()
        progress = (self.current_idx + 1) / max(len(self.segments), 1)
        self._prog_bar.place(x=0, y=0, relheight=1, width=max(2, int(total_w * progress)))

        self._idx_lbl.config(text=f"{self.current_idx + 1} / {len(self.segments)}")
        self._hint_lbl.config(fg=FG_DIM)
        self.animating = True
        self._canvas.delete("all")

        dispatch = {
            "fadein":     self._fx_fadein,
            "typewriter": self._fx_typewriter,
            "shake":      self._fx_shake,
            "wave":       self._fx_wave,
        }
        dispatch.get(effect, self._fx_fadein)(text, speed)

    # ── 效果：渐显 ──
    def _fx_fadein(self, text: str, speed: int = 30):
        c = self._canvas
        steps = 40
        step  = [0]

        def tick():
            t = min(step[0] / steps, 1.0)
            color = lerp_color(BG_DARK, FG_MAIN, t)
            c.delete("all")
            c.create_text(self._cx, self._cy, text=text,
                          font=("Microsoft YaHei", 16),
                          fill=color, width=self._cw - 60,
                          justify=tk.CENTER, tags="t")
            step[0] += 1
            if step[0] <= steps:
                self._after_id = c.after(speed, tick)
            else:
                self.animating = False
                self._hint_lbl.config(fg=FG_HINT)

        tick()

    # ── 效果：打字机 ──
    def _fx_typewriter(self, text: str, speed: int = 55):
        c = self._canvas
        idx = [0]

        def tick():
            partial = text[:idx[0]]
            cursor  = "▌" if idx[0] < len(text) else ""
            c.delete("all")
            c.create_text(self._cx, self._cy, text=partial + cursor,
                          font=("Microsoft YaHei", 16),
                          fill=FG_MAIN, width=self._cw - 60,
                          justify=tk.CENTER, tags="t")
            idx[0] += 1
            if idx[0] <= len(text):
                self._after_id = c.after(speed, tick)
            else:
                self.animating = False
                self._hint_lbl.config(fg=FG_HINT)

        tick()

    # ── 效果：震动（配合红色渐显） ──
    def _fx_shake(self, text: str, speed: int = 18):
        c = self._canvas
        SHAKE_COLOR = "#ff5555"
        SHAKE_TIMES = 22
        fi_steps    = 14
        fi_step     = [0]

        def fadein_tick():
            t = fi_step[0] / fi_steps
            color = lerp_color(BG_DARK, SHAKE_COLOR, t)
            c.delete("all")
            c.create_text(self._cx, self._cy, text=text,
                          font=("Microsoft YaHei", 18, "bold"),
                          fill=color, width=self._cw - 60,
                          justify=tk.CENTER)
            fi_step[0] += 1
            if fi_step[0] <= fi_steps:
                self._after_id = c.after(speed, fadein_tick)
            else:
                shake_tick(0)

        def shake_tick(s: int):
            if s >= SHAKE_TIMES:
                c.delete("all")
                c.create_text(self._cx, self._cy, text=text,
                              font=("Microsoft YaHei", 18, "bold"),
                              fill=SHAKE_COLOR, width=self._cw - 60,
                              justify=tk.CENTER)
                self.animating = False
                self._hint_lbl.config(fg=FG_HINT)
                return
            intensity = 1.0 - s / SHAKE_TIMES
            dx = int(random.randint(-10, 10) * intensity)
            dy = int(random.randint(-6,   6) * intensity)
            c.delete("all")
            c.create_text(self._cx + dx, self._cy + dy, text=text,
                          font=("Microsoft YaHei", 18, "bold"),
                          fill=SHAKE_COLOR, width=self._cw - 60,
                          justify=tk.CENTER)
            self._after_id = c.after(speed, lambda: shake_tick(s + 1))

        fadein_tick()

    # ── 效果：波浪（逐字弹入） ──
    def _fx_wave(self, text: str, speed: int = 22):
        c = self._canvas
        WAVE_COLOR = "#88ddbb"
        CHAR_W = 18
        LINE_H = 30

        # 预计算换行
        max_chars = max(1, (self._cw - 60) // CHAR_W)
        raw_lines = text.split("\n")
        lines: list[str] = []
        for raw in raw_lines:
            while len(raw) > max_chars:
                lines.append(raw[:max_chars])
                raw = raw[max_chars:]
            lines.append(raw)

        total_chars = sum(len(l) for l in lines)
        total_frames = total_chars * 3 + 30
        frame = [0]

        def tick():
            c.delete("all")
            char_idx = 0
            start_y  = self._cy - (len(lines) - 1) * LINE_H // 2
            for li, line in enumerate(lines):
                lx = self._cx - len(line) * CHAR_W // 2
                for ci, ch in enumerate(line):
                    appear_frame = char_idx * 3
                    if frame[0] >= appear_frame:
                        prog = min(1.0, (frame[0] - appear_frame) / 10)
                        bounce_y = int(math.sin(prog * math.pi) * -14)
                        col = lerp_color(BG_DARK, WAVE_COLOR, min(prog * 1.5, 1.0))
                        c.create_text(lx + ci * CHAR_W + CHAR_W // 2,
                                      start_y + li * LINE_H + bounce_y,
                                      text=ch,
                                      font=("Microsoft YaHei", 16),
                                      fill=col)
                    char_idx += 1
            frame[0] += 1
            if frame[0] <= total_frames:
                self._after_id = c.after(speed, tick)
            else:
                self.animating = False
                self._hint_lbl.config(fg=FG_HINT)

        tick()

    # ── 结局画面 ──
    def _show_ending(self):
        c = self._canvas
        c.delete("all")
        c.create_text(self._cx, self._cy - 28, text="— 终 —",
                      font=("Microsoft YaHei", 26, "bold"), fill="#666688")
        c.create_text(self._cx, self._cy + 28,
                      text="故事结束，感谢你的体验",
                      font=("Microsoft YaHei", 12), fill=FG_DIM)
        self._hint_lbl.config(text="按 [ESC] 返回主菜单", fg=FG_DIM)
        self.animating = False

    # ── 空格键：跳过动画 / 下一段 ──
    def _on_space(self, _=None):
        if self.animating:
            if self._after_id:
                self._canvas.after_cancel(self._after_id)
                self._after_id = None
            self.animating = False
            # 直接呈现最终文本
            if self.current_idx < len(self.segments):
                seg  = self.segments[self.current_idx]
                text = seg.get("text", "")
                eff  = seg.get("effect", "fadein")
                col  = "#ff5555" if eff == "shake" else (
                       "#88ddbb" if eff == "wave"  else FG_MAIN)
                self._canvas.delete("all")
                self._canvas.create_text(
                    self._cx, self._cy, text=text,
                    font=("Microsoft YaHei",
                          18 if eff == "shake" else 16,
                          "bold" if eff == "shake" else "normal"),
                    fill=col, width=self._cw - 60, justify=tk.CENTER)
            self._hint_lbl.config(fg=FG_HINT)
            return
        self.current_idx += 1
        self._show_segment()

    # ── ESC 返回主菜单 ──
    def _on_escape(self, _=None):
        if self._after_id:
            self._canvas.after_cancel(self._after_id)
        self.root.unbind("<space>")
        self.root.unbind("<Escape>")
        self.game.show_main_menu()

    # ── 画布尺寸属性（懒计算）──
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


# ─────────────────────────── 入口 ───────────────────────────
def main():
    root = tk.Tk()
    TextAdventureGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()

