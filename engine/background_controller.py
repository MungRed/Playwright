import os
import random
import time
import tkinter as tk

from PIL import Image, ImageTk

from engine.config import BG_DARK


class BackgroundController:
    BG_SOLID_TAG = "bg_solid_layer"
    BG_IMAGE_TAG = "bg_image_layer"

    def __init__(self, canvas: tk.Canvas, project_root: str):
        self.canvas = canvas
        self.project_root = project_root

        self._bg_path: str | None = None
        self._bg_prev_path: str | None = None
        self._bg_fading: bool = False
        self._bg_fade_start: float = 0.0
        self._bg_fade_duration: float = 0.0
        self._bg_shake_start: float = 0.0
        self._bg_shake_duration: float = 0.0
        self._bg_shake_strength: int = 0

        self._bg_tk_image: ImageTk.PhotoImage | None = None
        self._bg_cache: dict[str, Image.Image] = {}
        self._bg_resized_cache: dict[tuple[str, int, int], Image.Image] = {}
        self._last_render_key: tuple | None = None
        self._last_pos: tuple[int, int] = (0, 0)

    def configure_for_segment(self, seg: dict):
        bg = seg.get("background", {})
        if not isinstance(bg, dict):
            return

        image_path = self._resolve_asset_path(bg.get("image"))
        effects = self._extract_effects(bg)

        if image_path and image_path != self._bg_path:
            do_fade = "fade" in effects or "fadein" in effects
            self._bg_prev_path = self._bg_path
            self._bg_path = image_path
            self._bg_resized_cache.clear()
            if do_fade and self._bg_prev_path:
                self._bg_fading = True
                self._bg_fade_start = time.monotonic()
                self._bg_fade_duration = max(0.1, float(bg.get("fade_ms", 450)) / 1000.0)
            else:
                self._bg_fading = False
                self._bg_prev_path = None

        if "shake" in effects:
            self._bg_shake_start = time.monotonic()
            self._bg_shake_duration = max(0.08, float(bg.get("shake_ms", 380)) / 1000.0)
            self._bg_shake_strength = max(1, int(bg.get("shake_strength", 10)))

    def refresh(self):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        target = self._get_resized_bg(self._bg_path, width, height)

        if target is None:
            self.canvas.delete(self.BG_IMAGE_TAG)
            solid_items = self.canvas.find_withtag(self.BG_SOLID_TAG)
            if solid_items:
                solid_item = solid_items[0]
                self.canvas.coords(solid_item, 0, 0, width, height)
                self.canvas.itemconfig(solid_item, fill=BG_DARK, outline="")
            else:
                self.canvas.create_rectangle(
                    0, 0, width, height, fill=BG_DARK, outline="", tags=(self.BG_SOLID_TAG,)
                )
            self.canvas.tag_lower(self.BG_SOLID_TAG)
            self._last_render_key = ("solid", width, height)
            self._last_pos = (0, 0)
            return

        self.canvas.delete(self.BG_SOLID_TAG)

        composed = target
        if self._bg_fading and self._bg_prev_path:
            prev = self._get_resized_bg(self._bg_prev_path, width, height)
            if prev is not None:
                t = (time.monotonic() - self._bg_fade_start) / self._bg_fade_duration
                t = max(0.0, min(1.0, t))
                composed = Image.blend(prev, target, t)
                if t >= 1.0:
                    self._bg_fading = False
                    self._bg_prev_path = None
            else:
                self._bg_fading = False
                self._bg_prev_path = None

        shake_x, shake_y = self._current_shake_offset()
        render_key = (
            self._bg_path,
            self._bg_prev_path,
            width,
            height,
            round((time.monotonic() - self._bg_fade_start) * 1000) if self._bg_fading else -1,
            shake_x,
            shake_y,
        )

        existing = self.canvas.find_withtag(self.BG_IMAGE_TAG)
        if existing and render_key == self._last_render_key and self._last_pos == (shake_x, shake_y):
            return

        self._bg_tk_image = ImageTk.PhotoImage(composed)

        existing = self.canvas.find_withtag(self.BG_IMAGE_TAG)
        if existing:
            item = existing[0]
            if self.canvas.type(item) == "image":
                try:
                    self.canvas.itemconfig(item, image=self._bg_tk_image)
                    self.canvas.coords(item, shake_x, shake_y)
                except tk.TclError:
                    self.canvas.delete(self.BG_IMAGE_TAG)
                    self.canvas.create_image(
                        shake_x,
                        shake_y,
                        image=self._bg_tk_image,
                        anchor="nw",
                        tags=(self.BG_IMAGE_TAG,),
                    )
            else:
                self.canvas.delete(self.BG_IMAGE_TAG)
                self.canvas.create_image(
                    shake_x,
                    shake_y,
                    image=self._bg_tk_image,
                    anchor="nw",
                    tags=(self.BG_IMAGE_TAG,),
                )
        else:
            self.canvas.create_image(
                shake_x,
                shake_y,
                image=self._bg_tk_image,
                anchor="nw",
                tags=(self.BG_IMAGE_TAG,),
            )
        self.canvas.tag_lower(self.BG_IMAGE_TAG)
        self._last_render_key = render_key
        self._last_pos = (shake_x, shake_y)

    def on_resize(self):
        self._bg_resized_cache.clear()
        self._last_render_key = None

    @property
    def has_active_animation(self) -> bool:
        return self._bg_fading or self._bg_shake_duration > 0

    def _extract_effects(self, bg: dict) -> set[str]:
        effects_raw = bg.get("effects", [])
        if isinstance(effects_raw, str):
            effects = {effects_raw.lower()}
        elif isinstance(effects_raw, list):
            effects = {str(item).lower() for item in effects_raw}
        else:
            effects = set()

        effect_single = bg.get("effect")
        if isinstance(effect_single, str):
            effects.add(effect_single.lower())
        return effects

    def _resolve_asset_path(self, path: str | None) -> str | None:
        if not path:
            return None
        if os.path.isabs(path):
            return path if os.path.exists(path) else None
        abs_path = os.path.join(self.project_root, path)
        return abs_path if os.path.exists(abs_path) else None

    def _load_image(self, path: str) -> Image.Image | None:
        if path in self._bg_cache:
            return self._bg_cache[path]
        try:
            image = Image.open(path).convert("RGB")
            self._bg_cache[path] = image
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

    def _get_resized_bg(self, path: str | None, width: int, height: int) -> Image.Image | None:
        if not path:
            return None
        key = (path, width, height)
        if key in self._bg_resized_cache:
            return self._bg_resized_cache[key]
        image = self._load_image(path)
        if image is None:
            return None
        resized = self._resize_cover(image, width, height)
        self._bg_resized_cache[key] = resized
        return resized

    def _current_shake_offset(self) -> tuple[int, int]:
        if self._bg_shake_duration <= 0:
            return 0, 0
        elapsed = time.monotonic() - self._bg_shake_start
        if elapsed >= self._bg_shake_duration:
            self._bg_shake_duration = 0
            return 0, 0
        ratio = 1.0 - elapsed / self._bg_shake_duration
        intensity = max(1, int(self._bg_shake_strength * ratio))
        return random.randint(-intensity, intensity), random.randint(-intensity, intensity)
