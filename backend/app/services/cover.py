"""Playlist cover art: a 640x640 JPEG painted from the mood (no AI, no stock images).

- Colour follows positivity, like the mood orb on the website: deep blue when low,
  magenta-coral in the middle, warm orange when bright.
- Waves follow energy: calm moods get a few long, gentle waves; charged moods get many
  tight, tall ones.
- The playlist's headline and the mood words are set in Pillow's built-in font, with the
  Muse record mark in the corner and a little grain, like a printed sleeve.

Spotify accepts a base64 JPEG of at most 256 KB, so the image is kept under 190 KB.
"""

import colorsys
import io
import math
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SIZE = 640
MAX_JPEG_BYTES = 190_000  # base64 adds a third: 190 KB -> ~253 KB, under Spotify's 256 KB


def _rgb(hue: float, saturation: float, lightness: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360, lightness, saturation)
    return round(r * 255), round(g * 255), round(b * 255)


def mood_hue(valence: float) -> float:
    """The same mapping as the website's mood orb."""
    return (230 + valence * 160) % 360


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _record_mark(
    draw: ImageDraw.ImageDraw, x: int, y: int, r: int, accent: tuple[int, int, int]
) -> None:
    """Muse's logo: a record with a pulse shaped like an M."""
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(23, 18, 15))
    draw.ellipse(
        (x - r * 0.8, y - r * 0.8, x + r * 0.8, y + r * 0.8), outline=(60, 52, 46), width=1
    )
    draw.ellipse((x - r * 0.5, y - r * 0.5, x + r * 0.5, y + r * 0.5), fill=accent)
    s = r / 20
    points = [
        (5.5, 22),
        (9.7, 22),
        (12.3, 14.5),
        (16.5, 26.5),
        (20, 14),
        (23.5, 26.5),
        (27.7, 14.5),
        (30.3, 22),
        (34.5, 22),
    ]
    draw.line(
        [(x + (px - 20) * s, y + (py - 20) * s) for px, py in points],
        fill=(255, 247, 238),
        width=max(2, round(2.4 * s)),
        joint="curve",
    )


def make_cover(valence: float, energy: float, title: str, words: list[str]) -> bytes:
    """A JPEG cover for a playlist with this mood, headline and mood words."""
    valence = min(1.0, max(0.0, valence))
    energy = min(1.0, max(0.0, energy))
    hue = mood_hue(valence)
    light = _rgb(hue + 20, 0.6 + 0.3 * valence, 0.42 + 0.2 * valence)  # low moods are dimmer
    deep = _rgb(hue - 30, 0.7, 0.1 + 0.08 * energy)

    # 1. Diagonal gradient, light top-left to deep bottom-right (painted small, then smoothed)
    small = 64
    mask = Image.new("L", (small, small))
    mask.putdata(
        [round(255 * (x + y) / (2 * (small - 1))) for y in range(small) for x in range(small)]
    )
    mask = mask.resize((SIZE, SIZE), Image.Resampling.BICUBIC)
    cover = Image.composite(
        Image.new("RGB", (SIZE, SIZE), deep), Image.new("RGB", (SIZE, SIZE), light), mask
    )

    # 2. A soft glow, higher and brighter for brighter moods
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gy = int(SIZE * (0.45 - 0.2 * valence))
    ImageDraw.Draw(glow).ellipse(
        (SIZE * 0.35, gy - 170, SIZE * 0.35 + 380, gy + 210), fill=(*_rgb(hue + 40, 1.0, 0.75), 150)
    )
    cover = Image.alpha_composite(cover.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(70)))

    # 3. Waves: energy sets how many, how tall and how tight
    waves = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(waves)
    count = 3 + round(energy * 5)
    amplitude = 10 + energy * 38
    cycles = 1.2 + energy * 3.2
    for i in range(count):
        base = SIZE * 0.42 + i * (150 / max(1, count - 1))
        phase = i * 0.7
        points = [
            (
                x,
                base
                + amplitude
                * math.sin(2 * math.pi * cycles * x / SIZE + phase)
                * (0.6 + 0.4 * math.sin(x / 90 + i)),
            )
            for x in range(-10, SIZE + 11, 8)
        ]
        draw.line(points, fill=(255, 255, 255, 40 + 18 * (i % 3)), width=2, joint="curve")
    cover = Image.alpha_composite(cover, waves)

    # 4. Grain, like a printed sleeve
    grain = Image.effect_noise((SIZE, SIZE), 28).convert("RGBA")
    grain.putalpha(18)
    cover = Image.alpha_composite(cover, grain).convert("RGB")

    # 5. Mark, headline and mood words
    draw = ImageDraw.Draw(cover)
    _record_mark(draw, 64, 64, 26, _rgb(hue + 10, 0.95, 0.6))
    draw.text((102, 50), "MUSE", font=_font(26), fill=(255, 250, 242))
    lines = textwrap.wrap(" ".join(title.split())[:80], width=18)[:3] or ["Muse"]
    size = 58 if max(len(line) for line in lines) <= 14 else 48
    y = SIZE - 70 - (len(lines) * (size + 8)) - (40 if words else 0)
    for line in lines:
        draw.text((48, y), line, font=_font(size), fill=(255, 250, 242))
        y += size + 8
    if words:
        draw.text(
            (50, y + 10),
            "  ·  ".join(w[:20] for w in words[:3]).upper(),
            font=_font(22),
            fill=(255, 240, 225),
        )

    for quality in (88, 80, 72, 64):
        out = io.BytesIO()
        cover.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        if out.tell() <= MAX_JPEG_BYTES:
            break
    return out.getvalue()
