"""
文字演出效果
每个效果函数签名：fx_xxx(canvas, text, cx, cy, cw, speed, seg, on_done, set_after)
  - canvas    : tk.Canvas
  - text      : 要显示的文字
  - cx, cy    : 文字起点坐标（左上角）
  - cw        : 画布宽度（用于自动换行）
  - speed     : 每帧间隔毫秒
  - seg       : 当前段落字典（透传给 on_done）
  - on_done   : 动画结束时的回调 on_done(seg)
  - set_after : 存储 after_id 的回调 set_after(after_id)，供外部取消
"""

import tkinter as tk
import math
import random

from engine.config import BG_DARK, FG_MAIN
from engine.utils import lerp_color


def fx_fadein(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
              speed: int, seg: dict, on_done, set_after):
    """文字从背景色渐变为白色（淡入）"""
    STEPS = 40
    step = [0]

    def tick():
        t = min(step[0] / STEPS, 1.0)
        color = lerp_color(BG_DARK, FG_MAIN, t)
        canvas.delete("all")
        canvas.create_text(cx, cy, text=text,
                           font=("Microsoft YaHei", 16),
                           fill=color, width=cw - 80,
                           justify=tk.LEFT, anchor="nw")
        step[0] += 1
        if step[0] <= STEPS:
            set_after(canvas.after(speed, tick))
        else:
            on_done(seg)

    tick()


def fx_typewriter(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
                  speed: int, seg: dict, on_done, set_after):
    """逐字打字机效果，末尾有光标闪烁"""
    idx = [0]

    def tick():
        partial = text[:idx[0]]
        cursor  = "▌" if idx[0] < len(text) else ""
        canvas.delete("all")
        canvas.create_text(cx, cy, text=partial + cursor,
                           font=("Microsoft YaHei", 16),
                           fill=FG_MAIN, width=cw - 80,
                           justify=tk.LEFT, anchor="nw")
        idx[0] += 1
        if idx[0] <= len(text):
            set_after(canvas.after(speed, tick))
        else:
            on_done(seg)

    tick()


def fx_shake(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
             speed: int, seg: dict, on_done, set_after):
    """红色文字震动效果（适合危险/惊吓场景）"""
    SHAKE_COLOR = "#ff5555"
    SHAKE_TIMES = 22
    FI_STEPS    = 14
    fi_step     = [0]

    def fadein_tick():
        t = fi_step[0] / FI_STEPS
        color = lerp_color(BG_DARK, SHAKE_COLOR, t)
        canvas.delete("all")
        canvas.create_text(cx, cy, text=text,
                           font=("Microsoft YaHei", 18, "bold"),
                           fill=color, width=cw - 80,
                           justify=tk.LEFT, anchor="nw")
        fi_step[0] += 1
        if fi_step[0] <= FI_STEPS:
            set_after(canvas.after(speed, fadein_tick))
        else:
            shake_tick(0)

    def shake_tick(s: int):
        if s >= SHAKE_TIMES:
            canvas.delete("all")
            canvas.create_text(cx, cy, text=text,
                               font=("Microsoft YaHei", 18, "bold"),
                               fill=SHAKE_COLOR, width=cw - 80,
                               justify=tk.LEFT, anchor="nw")
            on_done(seg)
            return
        intensity = 1.0 - s / SHAKE_TIMES
        dx = int(random.randint(-8, 8) * intensity)
        dy = int(random.randint(-4, 4) * intensity)
        canvas.delete("all")
        canvas.create_text(cx + dx, cy + dy, text=text,
                           font=("Microsoft YaHei", 18, "bold"),
                           fill=SHAKE_COLOR, width=cw - 80,
                           justify=tk.LEFT, anchor="nw")
        set_after(canvas.after(speed, lambda: shake_tick(s + 1)))

    fadein_tick()


def fx_wave(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
            speed: int, seg: dict, on_done, set_after):
    """每个字符依次弹入，带反弹缓动（适合神秘/奇幻场景）"""
    import tkinter.font as tkfont
    WAVE_COLOR = "#88ddbb"
    FONT_SPEC  = ("Microsoft YaHei", 16)

    # 用真实字体度量，保证动画字符间距与 create_text 最终渲染完全一致
    fnt    = tkfont.Font(family=FONT_SPEC[0], size=FONT_SPEC[1])
    LINE_H = fnt.metrics("linespace") + 4   # 行高与 create_text 多行对齐

    def _char_w(ch: str) -> int:
        return fnt.measure(ch)

    # 按真实像素宽度换行，与 create_text(width=cw-80) 保持一致
    max_px    = cw - 80
    raw_lines = text.split("\n")
    lines: list[str] = []
    for raw in raw_lines:
        cur_line, cur_w = "", 0
        for ch in raw:
            w = _char_w(ch)
            if cur_w + w > max_px and cur_line:
                lines.append(cur_line)
                cur_line, cur_w = ch, w
            else:
                cur_line += ch
                cur_w    += w
        lines.append(cur_line)

    # 预计算每行每字符的 x 偏移（与 create_text 左对齐一致）
    char_positions: list[tuple[int, int, str]] = []  # (x, line_idx, ch)
    for li, line in enumerate(lines):
        cur_x = cx
        for ch in line:
            char_positions.append((cur_x, li, ch))
            cur_x += _char_w(ch)

    total_chars  = len(char_positions)
    total_frames = total_chars * 3 + 30
    frame        = [0]

    def tick():
        canvas.delete("all")
        for idx, (px, li, ch) in enumerate(char_positions):
            appear_frame = idx * 3
            if frame[0] >= appear_frame:
                prog     = min(1.0, (frame[0] - appear_frame) / 10)
                bounce_y = int(math.sin(prog * math.pi) * -14)
                col      = lerp_color(BG_DARK, WAVE_COLOR, min(prog * 1.5, 1.0))
                canvas.create_text(px, cy + li * LINE_H + bounce_y,
                                   text=ch,
                                   font=FONT_SPEC,
                                   fill=col,
                                   anchor="nw")
        frame[0] += 1
        if frame[0] <= total_frames:
            set_after(canvas.after(speed, tick))
        else:
            on_done(seg)

    tick()


# ── 效果注册表 ──
EFFECTS = {
    "fadein":     fx_fadein,
    "typewriter": fx_typewriter,
    "shake":      fx_shake,
    "wave":       fx_wave,
}

# 各效果跳过后的文字颜色
EFFECT_SKIP_COLOR = {
    "shake": "#ff5555",
    "wave":  "#88ddbb",
}
