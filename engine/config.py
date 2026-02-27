import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 脚本目录（相对于项目根目录）
SCRIPTS_DIR = os.path.join(_ROOT, "scripts")

# ── 背景色 ──
BG_DARK  = "#0d0d1a"
BG_MENU  = "#1a1a2e"
BG_CARD  = "#2d2d4e"
BG_HOVER = "#3d3d6e"

# ── 字体色 ──
FG_MAIN  = "#d0d0e8"
FG_DIM   = "#555577"
FG_HINT  = "#8888aa"

# ── 强调色 ──
ACCENT   = "#5566ff"
