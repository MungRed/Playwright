import glob
import json
import os
import random
import sys
import ctypes
import ctypes.wintypes
from dataclasses import dataclass

import pygame


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT, "scripts")

BG_DARK = (13, 13, 26)
BG_MENU = (26, 26, 46)
BG_CARD = (45, 45, 78)
BG_HOVER = (61, 61, 110)
FG_MAIN = (208, 208, 232)
FG_DIM = (95, 95, 122)
FG_HINT = (136, 136, 170)
SHAKE_RED = (255, 85, 85)
LEFT_BAR_WIDTH = 220
RIGHT_BAR_WIDTH = 260
CENTER_WIDTH = 1280
CENTER_HEIGHT = 720
MENU_WIDTH = 1280
MENU_HEIGHT = 720
OUTER_MARGIN = 16
TYPEWRITER_SPEED = 55
TYPEWRITER_CURSOR = "|"


@dataclass
class ScriptMeta:
    path: str
    title: str
    description: str


class PygameVNApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("剧本阅读器（pygame）")
        flags = pygame.RESIZABLE | pygame.DOUBLEBUF
        self.screen = self._set_window_size(MENU_WIDTH, MENU_HEIGHT, flags)

        self.clock = pygame.time.Clock()
        self.running = True
        self.mode = "menu"

        self.font_title = pygame.font.SysFont("Microsoft YaHei", 54, bold=True)
        self.font_h2 = pygame.font.SysFont("Microsoft YaHei", 26, bold=True)
        self.font_main = pygame.font.SysFont("Microsoft YaHei", 28)
        self.font_small = pygame.font.SysFont("Microsoft YaHei", 20)
        self.text_line_gap = 10

        self.scripts = self._load_scripts()
        self.menu_rects: list[tuple[pygame.Rect, ScriptMeta]] = []

        self.segments: dict[str, dict] = {}
        self.current_id = ""
        self.history: list[str] = []
        self.total_linear = 0
        self.script_title = ""

        self.step_texts: list[str] = []
        self.step_index = 0
        self.step_seg_id = ""

        self.animating = False
        self.anim_effect = "typewriter"
        self.anim_speed = 30
        self.anim_target_text = ""
        self.anim_char_index = 0
        self.anim_next_tick = 0
        self.anim_append_start = 0
        self.shake_until = 0

        self.bg_path: str | None = None
        self.bg_prev_path: str | None = None
        self.bg_fade_until = 0
        self.bg_fade_start = 0
        self.bg_fade_ms = 0
        self.bg_shake_until = 0
        self.bg_shake_strength = 0

        self.base_image_cache: dict[str, pygame.Surface] = {}
        self.scaled_image_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self.portrait_scaled_cache: dict[tuple[str, int, int], pygame.Surface] = {}
        self.character_image_path: str | None = None

    def run(self):
        while self.running:
            now = pygame.time.get_ticks()
            self._handle_events()
            self._update(now)
            self._draw(now)
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def _set_window_size(self, width: int, height: int, flags: int | None = None, preserve_center: bool = False) -> pygame.Surface:
        center = self._get_window_center() if preserve_center else None
        target_flags = flags if flags is not None else (pygame.RESIZABLE | pygame.DOUBLEBUF)
        try:
            screen = pygame.display.set_mode((width, height), target_flags, vsync=1)
        except TypeError:
            screen = pygame.display.set_mode((width, height), target_flags)

        if center is not None:
            self._move_window_center(center)
        return screen

    def _get_window_center(self) -> tuple[int, int] | None:
        if sys.platform != "win32":
            return None
        wm_info = pygame.display.get_wm_info()
        hwnd = wm_info.get("window")
        if not hwnd:
            return None
        rect = ctypes.wintypes.RECT()
        user32 = ctypes.windll.user32
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return None
        return ((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)

    def _move_window_center(self, center: tuple[int, int]):
        if sys.platform != "win32":
            return
        wm_info = pygame.display.get_wm_info()
        hwnd = wm_info.get("window")
        if not hwnd:
            return
        rect = ctypes.wintypes.RECT()
        user32 = ctypes.windll.user32
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        new_x = int(center[0] - width / 2)
        new_y = int(center[1] - height / 2)
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        user32.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0, SWP_NOSIZE | SWP_NOZORDER)

    def _load_scripts(self) -> list[ScriptMeta]:
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        result: list[ScriptMeta] = []
        for path in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                result.append(
                    ScriptMeta(
                        path=path,
                        title=data.get("title", os.path.basename(path)),
                        description=data.get("description", ""),
                    )
                )
            except Exception:
                continue
        return result

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                if self.mode == "menu":
                    self.screen = self._set_window_size(MENU_WIDTH, MENU_HEIGHT, preserve_center=True)
                else:
                    min_w = OUTER_MARGIN * 2 + LEFT_BAR_WIDTH + CENTER_WIDTH + RIGHT_BAR_WIDTH
                    min_h = CENTER_HEIGHT
                    new_w = max(min_w, event.w)
                    new_h = max(min_h, event.h)
                    self.screen = self._set_window_size(new_w, new_h)
                self.scaled_image_cache.clear()
                self.portrait_scaled_cache.clear()
            elif event.type == pygame.KEYDOWN:
                if self.mode == "menu":
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                else:
                    if event.key == pygame.K_ESCAPE:
                        self._back_to_menu()
                    elif event.key == pygame.K_SPACE:
                        self._advance()
                    elif event.key == pygame.K_BACKSPACE:
                        self._go_back()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.mode == "menu":
                    self._menu_click(event.pos)
                else:
                    self._advance()

    def _update(self, now: int):
        if self.mode == "reader":
            self._update_animation(now)

    def _draw(self, now: int):
        if self.mode == "menu":
            self._draw_menu()
        else:
            self._draw_reader(now)

    def _draw_menu(self):
        w, h = self.screen.get_size()
        self.screen.fill(BG_MENU)
        self.menu_rects.clear()

        title = self.font_title.render("剧本阅读器", True, FG_MAIN)
        self.screen.blit(title, (w // 2 - title.get_width() // 2, 42))
        subtitle = self.font_main.render("选择要阅读的剧本（pygame）", True, FG_HINT)
        self.screen.blit(subtitle, (w // 2 - subtitle.get_width() // 2, 116))

        panel = pygame.Rect(140, 170, w - 280, h - 250)
        pygame.draw.rect(self.screen, BG_DARK, panel, border_radius=14)

        y = panel.top + 24
        for item in self.scripts:
            card = pygame.Rect(panel.left + 24, y, panel.width - 48, 74)
            hover = card.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, BG_HOVER if hover else BG_CARD, card, border_radius=10)

            t = self.font_h2.render(item.title, True, FG_MAIN)
            self.screen.blit(t, (card.left + 14, card.top + 8))
            if item.description:
                d = self.font_small.render(item.description[:80], True, FG_HINT)
                self.screen.blit(d, (card.left + 14, card.top + 42))

            self.menu_rects.append((card, item))
            y += 86
            if y + 74 > panel.bottom - 8:
                break

        tip = self.font_small.render("ESC 退出", True, FG_DIM)
        self.screen.blit(tip, (w - tip.get_width() - 20, h - 30))

    def _menu_click(self, pos: tuple[int, int]):
        for rect, item in self.menu_rects:
            if rect.collidepoint(pos):
                self._start_script(item.path)
                return

    def _start_script(self, script_path: str):
        try:
            with open(script_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            self.segments = {"0": {"text": f"脚本加载失败：{exc}", "effect": "typewriter", "speed": TYPEWRITER_SPEED}}
            self.script_title = "加载失败"
            self.total_linear = 1
            self.current_id = "0"
            self.history = []
            self.mode = "reader"
            self._show_segment()
            return

        raw = data.get("segments", [])
        self.segments = {}
        if isinstance(raw, list):
            self.total_linear = len(raw)
            for i, seg in enumerate(raw):
                seg = dict(seg)
                seg.pop("choices", None)
                if "next" not in seg and i + 1 < len(raw):
                    seg["next"] = str(i + 1)
                self.segments[str(i)] = seg
            self.current_id = data.get("start", "0")
        else:
            self.total_linear = len(raw)
            for k, v in raw.items():
                seg = dict(v)
                seg.pop("choices", None)
                self.segments[str(k)] = seg
            self.current_id = data.get("start", next(iter(self.segments), ""))

        self.script_title = data.get("title", "剧本")
        self.history = []
        self.step_seg_id = ""
        self.step_texts = []
        self.step_index = 0
        self.screen = self._set_window_size(
            OUTER_MARGIN * 2 + LEFT_BAR_WIDTH + CENTER_WIDTH + RIGHT_BAR_WIDTH,
            CENTER_HEIGHT,
            preserve_center=True,
        )
        self.scaled_image_cache.clear()
        self.portrait_scaled_cache.clear()
        self.mode = "reader"
        self._show_segment()

    def _back_to_menu(self):
        self.mode = "menu"
        self.animating = False
        self.scripts = self._load_scripts()
        self.screen = self._set_window_size(MENU_WIDTH, MENU_HEIGHT, preserve_center=True)
        self.scaled_image_cache.clear()
        self.portrait_scaled_cache.clear()

    def _go_back(self):
        if self.animating or not self.history:
            return
        self.current_id = self.history.pop()
        self.step_seg_id = ""
        self.step_texts = []
        self.step_index = 0
        self._show_segment()

    def _advance(self):
        seg = self.segments.get(self.current_id, {})
        if self.animating:
            self.anim_char_index = len(self.anim_target_text)
            self.animating = False
            return

        if self.step_index + 1 < len(self.step_texts):
            self.step_index += 1
            self._show_segment()
            return

        next_id = seg.get("next")
        if next_id is not None:
            self.history.append(self.current_id)
            self.current_id = str(next_id)
            self.step_seg_id = ""
            self.step_texts = []
            self.step_index = 0
            self._show_segment()

    def _show_segment(self):
        seg = self.segments.get(self.current_id)
        if not seg:
            self.animating = False
            self.anim_target_text = "— 终 —\n故事结束，按 ESC 返回菜单"
            self.anim_char_index = len(self.anim_target_text)
            return

        if self.step_seg_id != self.current_id:
            self.step_texts = self._build_step_texts(seg)
            self.step_index = 0
            self.step_seg_id = self.current_id

        text = self.step_texts[self.step_index] if self.step_texts else self._normalize_text(str(seg.get("text", "")))
        effect = str(seg.get("effect", "typewriter")).lower()
        speed = int(seg.get("speed", TYPEWRITER_SPEED))

        if self.step_index == 0:
            self._configure_background(seg)

        self._configure_character(seg)

        self.anim_target_text = text
        self.anim_effect = effect
        self.anim_speed = TYPEWRITER_SPEED if effect == "typewriter" else max(8, speed)

        if self.step_index > 0 and self.step_texts:
            prev = self.step_texts[self.step_index - 1]
            self.anim_append_start = len(prev) if text.startswith(prev) else 0
        else:
            self.anim_append_start = 0

        now = pygame.time.get_ticks()
        if effect == "typewriter":
            self.anim_char_index = self.anim_append_start
            self.anim_next_tick = now
            self.animating = self.anim_char_index < len(self.anim_target_text)
        elif effect == "shake":
            self.anim_char_index = len(self.anim_target_text)
            self.shake_until = now + 420
            self.animating = True
        else:
            self.anim_char_index = len(self.anim_target_text)
            self.animating = False

    def _configure_background(self, seg: dict):
        bg = seg.get("background", {})
        if not isinstance(bg, dict):
            return
        path = self._resolve_asset_path(bg.get("image"))
        effects = self._extract_bg_effects(bg)

        if path and path != self.bg_path:
            self.bg_prev_path = self.bg_path
            self.bg_path = path
            if "fade" in effects and self.bg_prev_path:
                self.bg_fade_ms = int(bg.get("fade_ms", 450))
                self.bg_fade_start = pygame.time.get_ticks()
                self.bg_fade_until = self.bg_fade_start + max(100, self.bg_fade_ms)
            else:
                self.bg_prev_path = None
                self.bg_fade_start = 0
                self.bg_fade_until = 0

        if "shake" in effects:
            ms = int(bg.get("shake_ms", 360))
            self.bg_shake_until = pygame.time.get_ticks() + max(80, ms)
            self.bg_shake_strength = max(1, int(bg.get("shake_strength", 10)))

    def _configure_character(self, seg: dict):
        path = self._resolve_asset_path(seg.get("character_image"))
        if path:
            self.character_image_path = path

    def _update_animation(self, now: int):
        if not self.animating:
            return

        if self.anim_effect == "typewriter":
            while now >= self.anim_next_tick and self.anim_char_index < len(self.anim_target_text):
                self.anim_char_index += 1
                self.anim_next_tick += self.anim_speed
            if self.anim_char_index >= len(self.anim_target_text):
                self.animating = False
        elif self.anim_effect == "shake":
            if now >= self.shake_until:
                self.animating = False
        else:
            self.animating = False

    def _draw_reader(self, now: int):
        w, h = self.screen.get_size()
        self.screen.fill(BG_DARK)
        center_rect, left_rect, right_rect = self._reader_layout(w, h)

        bg_surface = self._get_scaled_bg(self.bg_path, center_rect.width, center_rect.height)
        if bg_surface:
            if self.bg_prev_path and now < self.bg_fade_until and self.bg_fade_until > self.bg_fade_start:
                prev = self._get_scaled_bg(self.bg_prev_path, center_rect.width, center_rect.height)
                if prev:
                    self.screen.blit(prev, center_rect.topleft)
                    t = (now - self.bg_fade_start) / max(1, self.bg_fade_until - self.bg_fade_start)
                    alpha = int(max(0, min(1, t)) * 255)
                    tmp = bg_surface.copy()
                    tmp.set_alpha(alpha)
                    self.screen.blit(tmp, center_rect.topleft)
                else:
                    self.screen.blit(bg_surface, center_rect.topleft)
            else:
                self.screen.blit(bg_surface, center_rect.topleft)
                if self.bg_prev_path and now >= self.bg_fade_until:
                    self.bg_prev_path = None
                    self.bg_fade_until = 0
                    self.bg_fade_start = 0

        sx = sy = 0
        if now < self.bg_shake_until:
            remain = max(0.0, (self.bg_shake_until - now) / 380.0)
            intensity = max(1, int(self.bg_shake_strength * remain))
            sx = random.randint(-intensity, intensity)
            sy = random.randint(-intensity, intensity)

        self._draw_sidebars(left_rect, right_rect)
        self._draw_text_overlay(center_rect, sx, sy)

    def _reader_layout(self, w: int, h: int) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
        usable_w = w - OUTER_MARGIN * 2
        center_x = OUTER_MARGIN + (usable_w // 2 - CENTER_WIDTH // 2)
        center_y = h // 2 - CENTER_HEIGHT // 2
        center_rect = pygame.Rect(center_x, center_y, CENTER_WIDTH, CENTER_HEIGHT)
        left_rect = pygame.Rect(center_rect.left - LEFT_BAR_WIDTH, center_rect.top, LEFT_BAR_WIDTH, CENTER_HEIGHT)
        right_rect = pygame.Rect(center_rect.right, center_rect.top, RIGHT_BAR_WIDTH, CENTER_HEIGHT)
        return center_rect, left_rect, right_rect

    def _draw_sidebars(self, left_rect: pygame.Rect, right_rect: pygame.Rect):
        left_layer = pygame.Surface((left_rect.width, left_rect.height), pygame.SRCALPHA)
        left_layer.fill((13, 13, 26, 175))
        self.screen.blit(left_layer, left_rect.topleft)

        right_layer = pygame.Surface((right_rect.width, right_rect.height), pygame.SRCALPHA)
        right_layer.fill((13, 13, 26, 175))
        self.screen.blit(right_layer, right_rect.topleft)

        self._draw_left_sidebar(left_rect)
        self._draw_right_sidebar(right_rect)

    def _draw_left_sidebar(self, left_rect: pygame.Rect):
        y = left_rect.top + 18
        x = left_rect.left + 18
        title = self.font_h2.render("进度", True, FG_MAIN)
        self.screen.blit(title, (x, y))
        y += 42

        progress = "-"
        if self.current_id.isdigit() and self.total_linear > 0:
            idx = int(self.current_id)
            pct = int((idx + 1) / max(1, self.total_linear) * 100)
            progress = f"{idx + 1}/{self.total_linear} ({pct}%)"

        p_text = self.font_small.render(progress, True, FG_HINT)
        self.screen.blit(p_text, (x, y))
        y += 30
        seg_text = self.font_small.render(f"当前段落: {self.current_id}", True, FG_HINT)
        self.screen.blit(seg_text, (x, y))

    def _draw_right_sidebar(self, right_rect: pygame.Rect):
        title = self.font_h2.render("人物", True, FG_MAIN)
        self.screen.blit(title, (right_rect.left + 18, right_rect.top + 18))

        max_pw = right_rect.width - 28
        max_ph = int(right_rect.height * 0.58)
        portrait = self._get_scaled_portrait(self.character_image_path, max_pw, max_ph)

        portrait_bottom = right_rect.top + 86
        if portrait is not None:
            frame_pad = 6
            frame_w = portrait.get_width() + frame_pad * 2
            frame_h = portrait.get_height() + frame_pad * 2
            frame_x = right_rect.left + (right_rect.width - frame_w) // 2
            frame_y = right_rect.top + 76
            frame = pygame.Rect(frame_x, frame_y, frame_w, frame_h)
            pygame.draw.rect(self.screen, (30, 30, 52), frame, border_radius=10)
            self.screen.blit(portrait, (frame.left + frame_pad, frame.top + frame_pad))
            portrait_bottom = frame.bottom + 14
        else:
            miss = self.font_small.render("未配置人物立绘", True, FG_DIM)
            self.screen.blit(miss, (right_rect.left + (right_rect.width - miss.get_width()) // 2, right_rect.top + 104))
            portrait_bottom = right_rect.top + 150

        ops_title = self.font_h2.render("操作", True, FG_MAIN)
        self.screen.blit(ops_title, (right_rect.left + 18, portrait_bottom))
        y = portrait_bottom + 42
        for line in (
            "空格 / 左键：继续",
            "动画中空格：跳过",
            "BackSpace：回退",
            "ESC：返回菜单",
        ):
            text = self.font_small.render(line, True, FG_HINT)
            self.screen.blit(text, (right_rect.left + 18, y))
            y += 30

    def _draw_text_overlay(self, center_rect: pygame.Rect, shake_x: int, shake_y: int):
        text_rect = pygame.Rect(center_rect.left + 18, center_rect.top + 18, center_rect.width - 36, center_rect.height - 36)

        if self.anim_effect == "typewriter" and self.animating:
            txt = self.anim_target_text[: self.anim_char_index]
            if self.anim_char_index < len(self.anim_target_text):
                txt += TYPEWRITER_CURSOR
        else:
            txt = self.anim_target_text[: self.anim_char_index]

        color = SHAKE_RED if self.anim_effect == "shake" else FG_MAIN
        offset_x = shake_x if self.anim_effect == "shake" and self.animating else 0
        offset_y = shake_y if self.anim_effect == "shake" and self.animating else 0
        self._draw_outlined_multiline(txt, self.font_main, color, text_rect, offset_x, offset_y)

    def _draw_outlined_multiline(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        ox: int = 0,
        oy: int = 0,
    ):
        lines = self._wrap_text(text, font, rect.width)
        line_h = font.get_linesize() + self.text_line_gap
        y = rect.top + oy
        for line in lines:
            base = font.render(line, True, color)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
                stroke = font.render(line, True, (0, 0, 0))
                self.screen.blit(stroke, (rect.left + ox + dx, y + dy))
            self.screen.blit(base, (rect.left + ox, y))
            y += line_h
            if y > rect.bottom:
                break

    @staticmethod
    def _normalize_text(text: str) -> str:
        while "\n\n" in text:
            text = text.replace("\n\n", "\n")
        return text

    def _wrap_text(self, text: str, font: pygame.font.Font, width: int) -> list[str]:
        out: list[str] = []
        for raw in text.split("\n"):
            if not raw:
                out.append("")
                continue
            cur = ""
            for ch in raw:
                test = cur + ch
                if font.size(test)[0] <= width or not cur:
                    cur = test
                else:
                    out.append(cur)
                    cur = ch
            if cur:
                out.append(cur)
        return out

    def _build_step_texts(self, seg: dict) -> list[str]:
        text = str(seg.get("text", "") or "")
        break_lines = seg.get("display_break_lines")
        if isinstance(break_lines, list):
            raw_lines = text.split("\n")
            if raw_lines:
                valid_points: list[int] = []
                max_line = len(raw_lines)
                for point in break_lines:
                    if isinstance(point, int) and 1 <= point < max_line and point not in valid_points:
                        valid_points.append(point)
                valid_points.sort()
                if valid_points:
                    ends = valid_points + [max_line]
                    return [self._normalize_text("\n".join(raw_lines[:end])) for end in ends]
        return [self._normalize_text(text)]

    def _extract_bg_effects(self, bg: dict) -> set[str]:
        effects_raw = bg.get("effects", [])
        if isinstance(effects_raw, str):
            effects = {effects_raw.lower()}
        elif isinstance(effects_raw, list):
            effects = {str(i).lower() for i in effects_raw}
        else:
            effects = set()
        single = bg.get("effect")
        if isinstance(single, str):
            effects.add(single.lower())
        return effects

    def _resolve_asset_path(self, path: str | None) -> str | None:
        if not path:
            return None
        if os.path.isabs(path):
            return path if os.path.exists(path) else None
        abs_path = os.path.join(ROOT, path)
        return abs_path if os.path.exists(abs_path) else None

    def _load_image(self, path: str) -> pygame.Surface | None:
        if path in self.base_image_cache:
            return self.base_image_cache[path]
        try:
            img = pygame.image.load(path).convert()
            self.base_image_cache[path] = img
            return img
        except Exception:
            return None

    def _scale_cover(self, image: pygame.Surface, width: int, height: int) -> pygame.Surface:
        src_w, src_h = image.get_size()
        if src_w <= 0 or src_h <= 0:
            return pygame.transform.smoothscale(image, (max(1, width), max(1, height)))
        scale = max(width / src_w, height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = pygame.transform.smoothscale(image, (new_w, new_h))
        rect = pygame.Rect((new_w - width) // 2, (new_h - height) // 2, width, height)
        return resized.subsurface(rect).copy()

    def _get_scaled_bg(self, path: str | None, width: int, height: int) -> pygame.Surface | None:
        if not path:
            return None
        key = (path, width, height)
        if key in self.scaled_image_cache:
            return self.scaled_image_cache[key]
        image = self._load_image(path)
        if image is None:
            return None
        scaled = self._scale_cover(image, width, height)
        self.scaled_image_cache[key] = scaled
        return scaled

    def _get_scaled_portrait(self, path: str | None, width: int, height: int) -> pygame.Surface | None:
        if not path:
            return None
        key = (path, width, height)
        if key in self.portrait_scaled_cache:
            return self.portrait_scaled_cache[key]
        image = self._load_image(path)
        if image is None:
            return None
        src_w, src_h = image.get_size()
        if src_w <= 0 or src_h <= 0:
            return None
        scale = min(width / src_w, height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = pygame.transform.smoothscale(image, (new_w, new_h))
        self.portrait_scaled_cache[key] = resized
        return resized


def run_app():
    app = PygameVNApp()
    app.run()
