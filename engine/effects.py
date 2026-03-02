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
import random

from engine.config import BG_DARK, FG_MAIN
from engine.text_render import upsert_outlined_text
from engine.utils import lerp_color


def fx_typewriter(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
                  speed: int, seg: dict, on_done, set_after, draw_base=None):
    """逐字打字机效果，末尾有光标闪烁"""
    idx = [0]

    def tick():
        partial = text[:idx[0]]
        cursor  = "▌" if idx[0] < len(text) else ""
        if draw_base:
            draw_base()
        upsert_outlined_text(canvas, "anim_text_outline", cx, cy,
                             text=partial + cursor,
                             font=("Microsoft YaHei", 16),
                             fill=FG_MAIN, width=cw - 80,
                             justify=tk.LEFT, anchor="nw",
                             tags=("text_layer",))
        idx[0] += 1
        if idx[0] <= len(text):
            set_after(canvas.after(speed, tick))
        else:
            on_done(seg)

    tick()


def fx_shake(canvas: tk.Canvas, text: str, cx: int, cy: int, cw: int,
             speed: int, seg: dict, on_done, set_after, draw_base=None):
    """红色文字震动效果（适合危险/惊吓场景）"""
    SHAKE_COLOR = "#ff5555"
    SHAKE_TIMES = 22
    FI_STEPS    = 14
    fi_step     = [0]

    def ramp_tick():
        t = fi_step[0] / FI_STEPS
        color = lerp_color(BG_DARK, SHAKE_COLOR, t)
        if draw_base:
            draw_base()
        upsert_outlined_text(canvas, "anim_text_outline", cx, cy,
                             text=text,
                             font=("Microsoft YaHei", 18, "bold"),
                             fill=color, width=cw - 80,
                             justify=tk.LEFT, anchor="nw",
                             tags=("text_layer",))
        fi_step[0] += 1
        if fi_step[0] <= FI_STEPS:
            set_after(canvas.after(speed, ramp_tick))
        else:
            shake_tick(0)

    def shake_tick(s: int):
        if s >= SHAKE_TIMES:
            upsert_outlined_text(canvas, "anim_text_outline", cx, cy,
                                 text=text,
                                 font=("Microsoft YaHei", 18, "bold"),
                                 fill=SHAKE_COLOR, width=cw - 80,
                                 justify=tk.LEFT, anchor="nw",
                                 tags=("text_layer",))
            on_done(seg)
            return
        intensity = 1.0 - s / SHAKE_TIMES
        dx = int(random.randint(-8, 8) * intensity)
        dy = int(random.randint(-4, 4) * intensity)
        if draw_base:
            draw_base()
        upsert_outlined_text(canvas, "anim_text_outline", cx + dx, cy + dy,
                             text=text,
                             font=("Microsoft YaHei", 18, "bold"),
                             fill=SHAKE_COLOR, width=cw - 80,
                             justify=tk.LEFT, anchor="nw",
                             tags=("text_layer",))
        set_after(canvas.after(speed, lambda: shake_tick(s + 1)))

    ramp_tick()


# ── 效果注册表 ──
EFFECTS = {
    "typewriter": fx_typewriter,
    "shake":      fx_shake,
}

# 各效果跳过后的文字颜色
EFFECT_SKIP_COLOR = {
    "shake": "#ff5555",
}
