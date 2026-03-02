"""Canvas 文本描边渲染工具。"""

import tkinter as tk

from engine.config import FG_MAIN


OUTLINE_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1), (0, 0))


def create_outlined_text(canvas: tk.Canvas, x: int, y: int, **kwargs):
    outline_fill = "#000000"
    for dx, dy in OUTLINE_OFFSETS[:-1]:
        stroke_kwargs = dict(kwargs)
        stroke_kwargs["fill"] = outline_fill
        canvas.create_text(x + dx, y + dy, **stroke_kwargs)
    canvas.create_text(x, y, **kwargs)


def upsert_outlined_text(canvas: tk.Canvas, key_tag: str, x: int, y: int, **kwargs):
    outline_fill = "#000000"
    ids = list(canvas.find_withtag(key_tag))

    if len(ids) != len(OUTLINE_OFFSETS):
        canvas.delete(key_tag)
        for idx, (dx, dy) in enumerate(OUTLINE_OFFSETS):
            item_kwargs = dict(kwargs)
            item_kwargs["fill"] = outline_fill if idx < len(OUTLINE_OFFSETS) - 1 else kwargs.get("fill", FG_MAIN)
            tags = tuple(dict.fromkeys((*(kwargs.get("tags", ())), key_tag)))
            item_kwargs["tags"] = tags
            canvas.create_text(x + dx, y + dy, **item_kwargs)
        return

    for idx, (item_id, (dx, dy)) in enumerate(zip(ids, OUTLINE_OFFSETS)):
        canvas.coords(item_id, x + dx, y + dy)
        item_fill = outline_fill if idx < len(OUTLINE_OFFSETS) - 1 else kwargs.get("fill", FG_MAIN)
        canvas.itemconfig(
            item_id,
            text=kwargs.get("text", ""),
            font=kwargs.get("font"),
            fill=item_fill,
            width=kwargs.get("width"),
            justify=kwargs.get("justify"),
            anchor=kwargs.get("anchor"),
        )
