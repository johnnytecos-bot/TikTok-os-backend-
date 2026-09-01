"""
card_renderer.py
Takes a quote + a template style and renders a finished PNG card, matching
the look of TikTok's native "Text post" styles (dark grid, notebook paper,
bordered card, etc). Fully local — no API calls, no cost, no rate limit.
"""

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from config import CARD_WIDTH, CARD_HEIGHT, FONT_DIR
from templates import TEMPLATES

# System fonts as a fallback if no custom fonts are dropped into assets/fonts/
_SYSTEM_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_SYSTEM_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _resolve_font_path(style: str) -> str:
    """Prefers a custom font dropped in assets/fonts/, falls back to system font."""
    custom = FONT_DIR / ("Bold.ttf" if style == "bold" else "Regular.ttf")
    if custom.exists():
        return str(custom)
    return _SYSTEM_BOLD if style == "bold" else _SYSTEM_REGULAR


def _draw_grid(draw: ImageDraw.ImageDraw, color: str, spacing: int = 60):
    for x in range(0, CARD_WIDTH, spacing):
        draw.line([(x, 0), (x, CARD_HEIGHT)], fill=color, width=1)
    for y in range(0, CARD_HEIGHT, spacing):
        draw.line([(0, y), (CARD_WIDTH, y)], fill=color, width=1)


def _draw_ruled_lines(draw: ImageDraw.ImageDraw, color: str, spacing: int = 90):
    for y in range(200, CARD_HEIGHT - 200, spacing):
        draw.line([(80, y), (CARD_WIDTH - 80, y)], fill=color, width=2)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _make_gradient_background(top_hex: str, bottom_hex: str) -> Image.Image:
    """Vertical top-to-bottom gradient — gives depth instead of a flat color."""
    top = _hex_to_rgb(top_hex)
    bottom = _hex_to_rgb(bottom_hex)
    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), top)
    pixels = img.load()
    for y in range(CARD_HEIGHT):
        t = y / CARD_HEIGHT
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(0, CARD_WIDTH, 4):  # step by 4px, then stretch — much faster, no visible banding
            pixels[x, y] = (r, g, b)
    # fill in the skipped columns cheaply by resizing down/up
    small = img.resize((CARD_WIDTH // 4, CARD_HEIGHT), Image.NEAREST)
    return small.resize((CARD_WIDTH, CARD_HEIGHT), Image.BILINEAR)


def _apply_vignette(img: Image.Image, strength: float = 0.32) -> Image.Image:
    """Darkens the edges so the center (where text sits) reads brighter — a camera-lens look."""
    vignette = Image.new("L", (CARD_WIDTH, CARD_HEIGHT), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse(
        [-CARD_WIDTH * 0.5, -CARD_HEIGHT * 0.35, CARD_WIDTH * 1.5, CARD_HEIGHT * 1.35],
        fill=255,
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(220))

    black = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0))
    # Blend black into the image where the vignette mask is dark (edges) — capped so
    # center stays close to full brightness and edges darken without going to pure black.
    inverted_mask = Image.eval(vignette, lambda px: int(255 - (255 - px) * strength))
    return Image.composite(img, black, inverted_mask)


def _draw_letterbox(draw: ImageDraw.ImageDraw, bar_height: int = 90):
    draw.rectangle([0, 0, CARD_WIDTH, bar_height], fill=(0, 0, 0))
    draw.rectangle([0, CARD_HEIGHT - bar_height, CARD_WIDTH, CARD_HEIGHT], fill=(0, 0, 0))


def _fit_font_size(draw, text: str, font_path: str, max_width: int, start_size: int = 88) -> ImageFont.FreeTypeFont:
    """Shrinks font size until the wrapped text fits the card width."""
    size = start_size
    while size > 30:
        font = ImageFont.truetype(font_path, size)
        wrapped = textwrap.fill(text, width=max(10, int(max_width / (size * 0.55))))
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=14)
        if (bbox[2] - bbox[0]) <= max_width:
            return font, wrapped
        size -= 4
    font = ImageFont.truetype(font_path, size)
    wrapped = textwrap.fill(text, width=20)
    return font, wrapped


def render_card(quote: str, template_id: str, output_path: Path) -> Path:
    """
    Renders `quote` onto the given template and saves it to output_path.
    Returns the path for convenience.
    """
    if template_id not in TEMPLATES:
        raise ValueError(f"Unknown template_id: {template_id}")

    style = TEMPLATES[template_id]

    if "bg_gradient" in style:
        top_hex, bottom_hex = style["bg_gradient"]
        img = _make_gradient_background(top_hex, bottom_hex)
    else:
        img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), style["bg_color"])

    if style.get("vignette"):
        img = _apply_vignette(img)

    draw = ImageDraw.Draw(img)

    if style.get("grid_lines"):
        _draw_grid(draw, style["accent_color"])
    if style.get("ruled_lines"):
        _draw_ruled_lines(draw, style["accent_color"])
    if style.get("letterbox"):
        _draw_letterbox(draw)

    if style.get("border_color"):
        border_width = 14
        draw.rectangle(
            [border_width // 2, border_width // 2,
             CARD_WIDTH - border_width // 2, CARD_HEIGHT - border_width // 2],
            outline=style["border_color"],
            width=border_width,
        )

    font_path = _resolve_font_path(style["font"])
    max_text_width = CARD_WIDTH - 160
    font, wrapped_text = _fit_font_size(draw, quote, font_path, max_text_width)

    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=14)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (CARD_WIDTH - text_w) / 2
    y = (CARD_HEIGHT - text_h) / 2

    if style.get("vignette"):  # cinematic-style templates get a soft drop shadow for depth
        shadow_offset = 4
        draw.multiline_text(
            (x + shadow_offset, y + shadow_offset), wrapped_text, font=font,
            fill=(0, 0, 0), spacing=14, align="center",
        )

    draw.multiline_text(
        (x, y), wrapped_text, font=font, fill=style["text_color"],
        spacing=14, align="center",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
