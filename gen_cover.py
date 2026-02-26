from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random, os

W, H = 1280, 720
img = Image.new("RGB", (W, H), "#0d0d1a")
draw = ImageDraw.Draw(img)

# ── 背景渐变（横向：深蓝→深紫）
for x in range(W):
    t = x / W
    r = int(13 + (30 - 13) * t)
    g = int(13 + (10 - 13) * t)
    b = int(26 + (46 - 26) * t)
    draw.line([(x, 0), (x, H)], fill=(r, g, b))

# ── 星场
random.seed(42)
for _ in range(300):
    sx = random.randint(0, W)
    sy = random.randint(0, H)
    size = random.choice([1, 1, 1, 2])
    a = random.randint(80, 220)
    draw.ellipse([sx, sy, sx + size, sy + size], fill=(a, a, min(255, int(a * 1.15))))

# ── hex → rgb
def h2r(hex_):
    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i:i+2], 16) for i in (0, 2, 4))

ACCENT = h2r("#5566ff")
cx, cy = W // 2, H // 2

# ── 竖向边框线
for i, x in enumerate([55, 65]):
    alpha = 180 - i * 70
    draw.line([(x, cy - 150), (x, cy + 150)], fill=(*ACCENT,), width=2)
for i, x in enumerate([W - 55, W - 65]):
    alpha = 180 - i * 70
    draw.line([(x, cy - 150), (x, cy + 150)], fill=(*ACCENT,), width=2)

# ── 水平装饰线
for y_off, half_w in [(168, 360), (174, 300)]:
    draw.line([(cx - half_w, cy - y_off), (cx + half_w, cy - y_off)], fill=ACCENT, width=1)
    draw.line([(cx - half_w, cy + y_off), (cx + half_w, cy + y_off)], fill=ACCENT, width=1)

# ── 字体加载
def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

font_title = load_font("C:/Windows/Fonts/arialbd.ttf", 100)
font_sub_cn = load_font("C:/Windows/Fonts/msyh.ttc", 36)
font_tag    = load_font("C:/Windows/Fonts/arial.ttf", 22)
font_mono   = load_font("C:/Windows/Fonts/consola.ttf", 15)

# ── 主标题发光层
title = "Playwright"
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
bbox = font_title.getbbox(title)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
tx = cx - tw // 2 - bbox[0]
ty = cy - th // 2 - 70 - bbox[1]
gd.text((tx, ty), title, font=font_title, fill=(85, 102, 255, 210))
glow = glow.filter(ImageFilter.GaussianBlur(22))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGBA")
draw = ImageDraw.Draw(img)

# ── 主标题文字
draw.text((tx, ty), title, font=font_title, fill="#dde2ff")

# ── 中文副标题
sub = "文 字 冒 险 游 戏 引 擎"
bbox2 = font_sub_cn.getbbox(sub)
sw = bbox2[2] - bbox2[0]
sx2 = cx - sw // 2 - bbox2[0]
sy2 = ty + th + 16
draw.text((sx2, sy2), sub, font=font_sub_cn, fill="#7788cc")

# ── 分隔点
dot_y = sy2 + 52
for dx in [-24, 0, 24]:
    draw.ellipse([(cx + dx - 3, dot_y - 3), (cx + dx + 3, dot_y + 3)], fill="#5566ff")



# ── 底部终端风格文字
lines_bot = [
    "> loading   《迷失之森》 ............ OK",
    "> loading   《午夜密室》 ............ OK",
    "> Press [SPACE] or click to advance_",
]
bot_y = H - 18 - len(lines_bot) * 21
for i, line in enumerate(lines_bot):
    brightness = 80 + i * 35
    draw.text((88, bot_y + i * 21), line, font=font_mono,
              fill=(brightness, brightness + 20, min(255, brightness + 60)))

# ── 右下角版本
ver = "v1.0  |  Python + tkinter"
vb = font_mono.getbbox(ver)
vw = vb[2] - vb[0]
draw.text((W - vw - 88 - vb[0], H - 30), ver, font=font_mono, fill="#2a3a55")

# ── 保存
_root = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(_root, "docs", "cover.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
img.convert("RGB").save(out, "PNG")
print("saved:", out)
