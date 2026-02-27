"""
文字演出效果
每个效果函数签名：fx_xxx(canvas, text, cx, cy, cw, speed, seg, on_done, set_after)
  - canvas    : tk.Canvas
  - text      : 要显示的文字
  - cx, cy    : 文字中心坐标
  - cw        : 画布宽度（用于自动换行）
  - speed     : 每帧间隔毫秒
  - seg       : 当前段落字典（透传给 on_done）
  - on_done   : 动画结束时的回调 on_done(seg)
  - set_after : 存储 after_id 的回调 set_after(after_id)，供外部取消
"""

import tkinter as tk
import math
import random
import unicodedata

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
                           fill=color, width=cw - 60,
                           justify=tk.CENTER)
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
                           fill=FG_MAIN, width=cw - 60,
                           justify=tk.CENTER)
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
                           fill=color, width=cw - 60,
                           justify=tk.CENTER)
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
                               fill=SHAKE_COLOR, width=cw - 60,
                               justify=tk.CENTER)
            on_done(seg)
            return
        intensity = 1.0 - s / SHAKE_TIMES
        dx = int(random.randint(-10, 10) * intensity)
        dy = int(random.randint(-6,   6) * intensity)
        canvas.delete("all")
        canvas.create_text(cx + dx, cy + dy, text=text,
                           font=("Microsoft YaHei", 18, "bold"),
                           fill=SHAKE_COLOR, width=cw - 60,
                           justify=tk.CENTER)
        set_after(canvas.after(speed, lambda: shake_tick(s + 1)))

    fadein_tick()


def fx_wave(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
            speed: int, seg: dict, on_done, set_after):
    """每个字符依次弹入，带反弹缓动（适合神秘/奇幻场景）"""
    WAVE_COLOR = "#88ddbb"
    UNIT_W     = 9    # ASCII 半角字符像素宽
    LINE_H     = 30

    def _char_w(ch: str) -> int:
        """CJK 全角字符返回 2 倍单元宽，其余返回 1 倍"""
        return UNIT_W * 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else UNIT_W

    def _line_px(line: str) -> int:
        return sum(_char_w(ch) for ch in line)

    # 预计算换行（按像素宽度截断）
    max_px    = cw - 60
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

    total_chars  = sum(len(l) for l in lines)
    total_frames = total_chars * 3 + 30
    frame        = [0]

    def tick():
        canvas.delete("all")
        char_idx = 0
        start_y  = cy - (len(lines) - 1) * LINE_H // 2
        for li, line in enumerate(lines):
            lx    = cx - _line_px(line) // 2
            cur_x = lx
            for ch in line:
                cw_ch        = _char_w(ch)
                appear_frame = char_idx * 3
                if frame[0] >= appear_frame:
                    prog     = min(1.0, (frame[0] - appear_frame) / 10)
                    bounce_y = int(math.sin(prog * math.pi) * -14)
                    col      = lerp_color(BG_DARK, WAVE_COLOR, min(prog * 1.5, 1.0))
                    canvas.create_text(cur_x + cw_ch // 2,
                                       start_y + li * LINE_H + bounce_y,
                                       text=ch,
                                       font=("Microsoft YaHei", 16),
                                       fill=col)
                cur_x    += cw_ch
                char_idx += 1
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
