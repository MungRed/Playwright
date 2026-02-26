"""颜色工具函数"""


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def lerp_color(c1_hex: str, c2_hex: str, t: float) -> str:
    """在两个十六进制颜色之间线性插值，t ∈ [0, 1]"""
    a, b = hex_to_rgb(c1_hex), hex_to_rgb(c2_hex)
    r = a[0] + (b[0] - a[0]) * t
    g = a[1] + (b[1] - a[1]) * t
    bv = a[2] + (b[2] - a[2]) * t
    return rgb_to_hex(r, g, bv)
