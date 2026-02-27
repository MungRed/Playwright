import os
import tkinter as tk

from PIL import Image, ImageTk

from engine.config import BG_CARD, BG_HOVER, FG_DIM, FG_HINT, FG_MAIN


class CharacterPanel(tk.Frame):
    def __init__(self, parent: tk.Widget, project_root: str, width: int = 280):
        super().__init__(parent, bg=BG_CARD, width=width)
        self.pack_propagate(False)

        self.project_root = project_root
        self._default_portrait_path = os.path.join(self.project_root, "docs", "scenes", "test_character_detective.png")
        self._portrait_cache: dict[str, Image.Image] = {}
        self._portrait_tk_image: ImageTk.PhotoImage | None = None
        self._last_portrait_path: str | None = None

        tk.Label(self, text="人物", font=("Microsoft YaHei", 10, "bold"),
                 fg=FG_MAIN, bg=BG_CARD).pack(anchor="w", padx=14, pady=(12, 6))

        self._speaker_name_lbl = tk.Label(self, text="说话人：-",
                                          font=("Microsoft YaHei", 10),
                                          fg=FG_HINT, bg=BG_CARD,
                                          anchor="w", justify=tk.LEFT)
        self._speaker_name_lbl.pack(fill=tk.X, padx=14)

        portrait_wrap = tk.Frame(self, bg=BG_HOVER, height=470)
        portrait_wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=(10, 10))
        portrait_wrap.pack_propagate(False)

        self._portrait_lbl = tk.Label(portrait_wrap, text="", bg=BG_HOVER)
        self._portrait_lbl.pack(fill=tk.BOTH, expand=True)
        self._portrait_lbl.bind("<Configure>", self._on_portrait_resize)

        self._speaker_hint_lbl = tk.Label(self, text="人物形象随当前段落更新",
                                          font=("Microsoft YaHei", 9),
                                          fg=FG_DIM, bg=BG_CARD,
                                          anchor="w", justify=tk.LEFT)
        self._speaker_hint_lbl.pack(fill=tk.X, padx=14, pady=(0, 10))

    def update_segment(self, seg: dict):
        speaker = str(seg.get("speaker", "旁白"))
        self._speaker_name_lbl.config(text=f"说话人：{speaker}")
        resolved = self._resolve_asset_path(seg.get("character_image"))
        if resolved:
            self._last_portrait_path = resolved
        elif self._last_portrait_path is None:
            default_resolved = self._resolve_asset_path(self._default_portrait_path)
            self._last_portrait_path = default_resolved or self._default_portrait_path
        self._render_portrait()

    def _on_portrait_resize(self, _=None):
        self._render_portrait()

    def _render_portrait(self):
        if not self._last_portrait_path:
            return
        image = self._load_image(self._last_portrait_path)
        if image is None:
            if self._portrait_tk_image is None:
                self._portrait_lbl.config(image="", text="无可用人物图", fg=FG_DIM, font=("Microsoft YaHei", 10))
            return

        self._portrait_lbl.update_idletasks()
        w = self._portrait_lbl.winfo_width() or 220
        h = self._portrait_lbl.winfo_height() or 440
        resized = self._resize_cover(image, max(1, w), max(1, h))
        self._portrait_tk_image = ImageTk.PhotoImage(resized)
        self._portrait_lbl.config(image=self._portrait_tk_image, text="")

    def _resolve_asset_path(self, path: str | None) -> str | None:
        if not path:
            return None
        if os.path.isabs(path):
            return path if os.path.exists(path) else None
        abs_path = os.path.join(self.project_root, path)
        return abs_path if os.path.exists(abs_path) else None

    def _load_image(self, path: str) -> Image.Image | None:
        if path in self._portrait_cache:
            return self._portrait_cache[path]
        try:
            image = Image.open(path).convert("RGB")
            self._portrait_cache[path] = image
            return image
        except Exception:
            return None

    @staticmethod
    def _resize_cover(image: Image.Image, width: int, height: int) -> Image.Image:
        src_w, src_h = image.size
        if src_w <= 0 or src_h <= 0:
            return image.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)
        scale = max(width / src_w, height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = max(0, (new_w - width) // 2)
        top = max(0, (new_h - height) // 2)
        return resized.crop((left, top, left + width, top + height))
