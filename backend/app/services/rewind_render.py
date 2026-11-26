"""Muse Rewind pages: story-sized (1080x1920) full-colour pages, painted with Pillow.

One idea per page, big type and bold colour blocks, in the website's own fonts (Inter
and Fraunces, Latin subset, SIL Open Font License; see assets/fonts/LICENSE.txt).
``rewind_pdf`` puts the pages in one PDF; ``rewind_preview`` makes a small strip of
them for the website. Nothing is saved on the server.
"""

import io
import math
import random
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.services.cover import _record_mark, _rgb, mood_hue
from app.services.rewind import Rewind

W, H = 1080, 1920
PAD = 84
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
RGB = tuple[int, int, int]


def _hex(value: str) -> RGB:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


CREAM, BLACK = _hex("#FFF4E6"), _hex("#17120F")
TANGERINE, PINK, VIOLET = _hex("#E4572E"), _hex("#FF4FA3"), _hex("#2B1B5A")
LIME, COBALT, SUN, GREEN = _hex("#C6F432"), _hex("#2F4BFF"), _hex("#FFC93C"), _hex("#13875A")
SKY = _hex("#3D8FD6")
TILE_COLOURS = (TANGERINE, LIME, PINK, SUN, COBALT, GREEN)

# page -> (background, ink, accent)
PALETTES: dict[str, tuple[RGB, RGB, RGB]] = {
    "cover": (VIOLET, CREAM, SUN),
    "mood_word": (PINK, BLACK, CREAM),
    "personality": (VIOLET, CREAM, LIME),
    "journey": (CREAM, BLACK, TANGERINE),
    "golden_hour": (SUN, BLACK, TANGERINE),
    "sound": (COBALT, CREAM, LIME),
    "match": (LIME, BLACK, VIOLET),
    "learned": (TANGERINE, CREAM, SUN),
    "playlists": (GREEN, CREAM, SUN),
    "outro": (BLACK, CREAM, TANGERINE),
}

DAY_PART_LABELS = {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening"}


# ---------------------------------------------------------------- type


@lru_cache(maxsize=64)
def font(display: bool, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    name = "Fraunces-latin.woff2" if display else "Inter-latin.woff2"
    loaded = ImageFont.truetype(str(FONTS / name), size)
    loaded.set_variation_by_axes([weight])
    return loaded


@lru_cache(maxsize=1)
def _missing_glyph() -> bytes:
    return bytes(font(False, 40).getmask("अ"))  # a letter the Latin subset lacks


@lru_cache(maxsize=4096)
def _has_glyph(char: str) -> bool:
    if char.isspace() or char.isascii():
        return True
    return bytes(font(False, 40).getmask(char)) != _missing_glyph()


def safe(text: str) -> str:
    """Drops characters the fonts can't draw (e.g. Devanagari), so no boxes appear."""
    kept = "".join(c for c in text if _has_glyph(c))
    return " ".join(kept.split())


def wrap(text: str, typeface: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for word in text.split():
        if lines and typeface.getlength(f"{lines[-1]} {word}") <= width:
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    return lines or [""]


def fitted(
    text: str, display: bool, weight: int, largest: int, width: int, smallest: int = 36
) -> ImageFont.FreeTypeFont:
    """The largest size (down to ``smallest``) at which ``text`` fits on one line."""
    size = largest
    while size > smallest and font(display, size, weight).getlength(text) > width:
        size -= 6
    return font(display, size, weight)


class Page:
    def __init__(self, kind: str, number: int, total: int, seed: int) -> None:
        self.background, self.ink, self.accent = PALETTES[kind]
        # An RGB canvas: drawing with RGBA colours on it blends (on an RGBA canvas the
        # alpha would be written into the image instead).
        self.image = Image.new("RGB", (W, H), self.background)
        self.draw = ImageDraw.Draw(self.image, "RGBA")
        self.random = random.Random(seed * 7919 + number)  # noqa: S311 - decoration only
        self.number, self.total = number, total

    def overlay(self, layer: Image.Image) -> None:
        """Composites a transparent layer onto the page."""
        self.image = Image.alpha_composite(self.image.convert("RGBA"), layer).convert("RGB")
        self.draw = ImageDraw.Draw(self.image, "RGBA")

    # decorations
    def blobs(self, colour: RGB, count: int = 3, alpha: int = 60) -> None:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for _ in range(count):
            r = self.random.randint(180, 420)
            x = self.random.choice([self.random.randint(-120, 200), self.random.randint(880, 1200)])
            y = self.random.randint(150, H - 150)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*colour, alpha))
        self.overlay(layer.filter(ImageFilter.GaussianBlur(8)))

    def squiggle(self, colour: RGB, y: int, amplitude: int = 26, width: int = 10) -> None:
        cycles = self.random.uniform(2.2, 3.6)
        phase = self.random.uniform(0, math.tau)
        points = [
            (x, y + amplitude * math.sin(phase + math.tau * cycles * x / W))
            for x in range(-20, W + 21, 6)
        ]
        self.draw.line(points, fill=(*colour, 255), width=width, joint="curve")

    def dots(self, colour: RGB, x0: int, y0: int, cols: int = 6, rows: int = 4) -> None:
        for i in range(cols):
            for j in range(rows):
                cx, cy = x0 + i * 34, y0 + j * 34
                self.draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(*colour, 170))

    def chrome(self, period: str) -> None:
        _record_mark(self.draw, PAD + 22, PAD + 22, 22, self.accent)
        self.text((PAD + 58, PAD + 6), "MUSE REWIND", font(False, 28, 800), spacing=3)
        page = f"{self.number} / {self.total}"
        self.text((W - PAD, PAD + 8), page, font(False, 28, 600), anchor="ra")
        self.text((PAD, H - PAD - 30), period, font(False, 26, 500), alpha=170)

    def text(
        self,
        xy: tuple[float, float],
        value: str,
        typeface: ImageFont.FreeTypeFont,
        fill: RGB | None = None,
        anchor: str = "la",
        alpha: int = 255,
        spacing: int = 0,
    ) -> None:
        colour = (*(fill or self.ink), alpha)
        if spacing:  # letter-spaced caps for small labels
            x, y = xy
            if anchor.startswith("r"):
                x -= typeface.getlength(value) + spacing * (len(value) - 1)
            for char in value:
                self.draw.text((x, y), char, font=typeface, fill=colour)
                x += typeface.getlength(char) + spacing
            return
        self.draw.text(xy, value, font=typeface, fill=colour, anchor=anchor)

    def paragraph(
        self,
        x: float,
        y: float,
        value: str,
        typeface: ImageFont.FreeTypeFont,
        width: int,
        fill: RGB | None = None,
        leading: float = 1.18,
        alpha: int = 255,
    ) -> float:
        size = typeface.size
        for line in wrap(value, typeface, width):
            self.text((x, y), line, typeface, fill, alpha=alpha)
            y += size * leading
        return y

    def kicker(self, y: int, value: str) -> None:
        label = font(False, 32, 800)
        width = label.getlength(value) + 3 * (len(value) - 1)
        self.draw.rounded_rectangle(
            (PAD - 4, y - 14, PAD + width + 36, y + 50), radius=32, fill=(*self.ink, 255)
        )
        self.text((PAD + 16, y), value, label, fill=self.background, spacing=3)

    def pill(self, x: float, y: float, value: str, bg: RGB, fg: RGB, size: int = 40) -> float:
        typeface = font(False, size, 700)
        w = typeface.getlength(value) + size * 1.2
        h = size * 1.9
        self.draw.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=(*bg, 255))
        self.text((x + w / 2, y + h / 2), value, typeface, fill=fg, anchor="mm")
        return w

    def pills(self, y: float, values: list[str], colours: tuple[RGB, ...], size: int = 40) -> float:
        x = PAD
        h = size * 1.9
        for i, value in enumerate(values):
            typeface = font(False, size, 700)
            w = typeface.getlength(value) + size * 1.2
            if x + w > W - PAD and x > PAD:
                x, y = PAD, y + h + 18
            bg = colours[i % len(colours)]
            self.pill(x, y, value, bg, BLACK if bg in (LIME, SUN, CREAM, PINK) else CREAM, size)
            x += w + 16
        return y + h

    def finish(self) -> Image.Image:
        return self.image


def _mood_colour(valence: float) -> RGB:
    return _rgb(mood_hue(valence), 0.82, 0.56)


def _mood_map(page: Page, x: int, y: int, size: int, r: Rewind, *, path: bool = True) -> None:
    """The positivity x energy map with the moods on it, oldest to newest."""
    ink = page.ink
    draw = page.draw
    draw.rounded_rectangle((x, y, x + size, y + size), radius=44, fill=(*ink, 22))
    mid = size / 2
    for i in range(0, size, 28):  # dashed mid-lines
        draw.line((x + mid, y + i, x + mid, y + i + 12), fill=(*ink, 70), width=3)
        draw.line((x + i, y + mid, x + i + 12, y + mid), fill=(*ink, 70), width=3)
    corner = font(False, 26, 700)
    page.text((x + 28, y + 24), "TENSE & WIRED", corner, alpha=150)
    page.text((x + size - 28, y + 24), "BRIGHT & LIVELY", corner, anchor="ra", alpha=150)
    page.text((x + 28, y + size - 52), "LOW & SLOW", corner, alpha=150)
    page.text((x + size - 28, y + size - 52), "CALM & CONTENT", corner, anchor="ra", alpha=150)

    def at(v: float, e: float) -> tuple[float, float]:
        return x + 40 + v * (size - 80), y + 40 + (1 - e) * (size - 80)

    points = r.moods
    if path and len(points) > 1:
        draw.line(
            [at(p.valence, p.energy) for p in points],
            fill=(*page.accent, 200),
            width=6,
            joint="curve",
        )
    last = len(points) - 1
    for i, p in enumerate(points):
        cx, cy = at(p.valence, p.energy)
        age = i / last if last else 1
        radius = 13 + 9 * age
        if i == last:
            draw.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), outline=(*ink, 200), width=5)
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(*_mood_colour(p.valence), 255),
            outline=(*CREAM, 255),
            width=4,
        )
    if path and len(points) > 1:
        sx, sy = at(points[0].valence, points[0].energy)
        page.text((sx, sy + 30), "START", font(False, 24, 800), anchor="ma")
        ex, ey = at(points[-1].valence, points[-1].energy)
        page.text((ex, ey - 50), "NOW", font(False, 24, 800), anchor="md")


# ---------------------------------------------------------------- pages


def _cover(page: Page, r: Rewind) -> None:
    v = r.trajectory.average.valence if r.trajectory and r.trajectory.average else 0.62
    e = r.trajectory.average.energy if r.trajectory and r.trajectory.average else 0.55
    hue = mood_hue(v)
    light, deep = _rgb(hue + 25, 0.85, 0.55), _rgb(hue - 40, 0.75, 0.16)
    small = Image.new("L", (32, 64))
    small.putdata(
        [round(255 * (0.3 * x / 31 + 0.7 * y / 63)) for y in range(64) for x in range(32)]
    )
    mask = small.resize((W, H), Image.Resampling.BICUBIC)
    base = Image.composite(Image.new("RGB", (W, H), deep), Image.new("RGB", (W, H), light), mask)
    page.image = base
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((380, 260, 1300, 1180), fill=(*_rgb(hue + 50, 1.0, 0.7), 170))
    page.overlay(glow.filter(ImageFilter.GaussianBlur(120)))
    for i in range(4 + round(e * 5)):  # waves: more and taller with more energy
        base_y = 1590 + i * 30
        amp = 18 + e * 50
        points = [
            (x, base_y + amp * math.sin(math.tau * (1.4 + e * 2.5) * x / W + i * 0.8))
            for x in range(-10, W + 11, 8)
        ]
        page.draw.line(points, fill=(255, 255, 255, 50 + 20 * (i % 3)), width=4, joint="curve")

    # a big record, half off the page
    rx, ry, rr = W - 40, 520, 330
    page.draw.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), fill=(*BLACK, 235))
    for k in range(5):
        g = rr - 40 - k * 36
        page.draw.ellipse((rx - g, ry - g, rx + g, ry + g), outline=(70, 60, 54, 255), width=2)
    page.draw.ellipse((rx - 110, ry - 110, rx + 110, ry + 110), fill=(*SUN, 255))
    page.draw.ellipse((rx - 14, ry - 14, rx + 14, ry + 14), fill=(*BLACK, 255))

    _record_mark(page.draw, PAD + 30, PAD + 30, 30, SUN)
    page.text((PAD + 78, PAD + 10), "MUSE", font(False, 40, 800), fill=CREAM, spacing=4)
    owner = safe(f"{r.title_owner} {r.span}")
    page.text((PAD, 900), owner, fitted(owner, True, 600, 96, W - 2 * PAD), fill=CREAM)
    page.text((PAD, 1000), "REWIND", fitted("REWIND", True, 900, 260, W - 2 * PAD), fill=SUN)
    page.text((PAD, 1290), r.period, font(False, 44, 600), fill=CREAM)
    page.paragraph(
        PAD,
        1390,
        "How you felt, what you played, and what Muse learned along the way.",
        font(False, 46, 500),
        W - 2 * PAD,
        fill=CREAM,
    )
    page.text(
        (PAD, H - PAD - 30),
        f"Made by Muse on {r.generated}",
        font(False, 28, 600),
        fill=CREAM,
        alpha=190,
    )


def _mood_word(page: Page, r: Rewind) -> None:
    page.blobs(CREAM, 3, 70)
    page.chrome(r.period)
    page.kicker(260, f"YOUR MOOD OF THE {r.span.upper()}")
    word = safe(r.top_mood or "").upper()
    page.text((PAD - 6, 400), word, fitted(word, True, 900, 300, W - 2 * PAD + 10))
    page.squiggle(CREAM, 760, 30, 14)
    y = page.paragraph(
        PAD,
        860,
        f"{r.top_mood_share}% of your moods were {safe(r.top_mood or '')}.",
        font(True, 70, 700),
        W - 2 * PAD,
    )
    if r.trajectory and len(r.trajectory.top_labels) > 1:
        page.text((PAD, y + 70), "THE RUNNERS-UP", font(False, 30, 800), spacing=3)
        y += 140
        most = r.trajectory.top_labels[0].count
        for i, item in enumerate(r.trajectory.top_labels[1:3]):
            width = 260 + 560 * item.count / most
            colour = (CREAM, VIOLET)[i % 2]
            page.draw.rounded_rectangle(
                (PAD, y, PAD + width, y + 110), radius=55, fill=(*colour, 255)
            )
            fg = BLACK if colour == CREAM else CREAM
            page.text(
                (PAD + 44, y + 55),
                safe(item.label).capitalize(),
                font(False, 46, 800),
                fill=fg,
                anchor="lm",
            )
            page.text(
                (PAD + width - 40, y + 55),
                f"x{item.count}",
                font(False, 40, 700),
                fill=fg,
                anchor="rm",
            )
            y += 140
    page.dots(BLACK, W - PAD - 170, H - 340)


def _personality(page: Page, r: Rewind) -> None:
    page.blobs(PINK, 2, 70)
    page.chrome(r.period)
    page.kicker(260, "YOUR MUSE PERSONALITY")
    if r.personality is None:  # the page is only made when there is one
        return
    y = 380.0
    for line in wrap(r.personality.name, font(True, 140, 900), W - 2 * PAD):
        page.text((PAD, y), line, font(True, 140, 900), fill=LIME)
        y += 150
    y = page.paragraph(PAD, y + 40, r.personality.line, font(False, 52, 500), W - 2 * PAD)

    # where "you" sit on a mini map
    size, x0, y0 = 560, (W - 560) // 2, max(int(y) + 90, 1020)
    page.draw.rounded_rectangle((x0, y0, x0 + size, y0 + size), radius=40, fill=(*CREAM, 30))
    page.draw.line((x0 + size / 2, y0, x0 + size / 2, y0 + size), fill=(*CREAM, 90), width=3)
    page.draw.line((x0, y0 + size / 2, x0 + size, y0 + size / 2), fill=(*CREAM, 90), width=3)
    if r.trajectory and r.trajectory.average:
        av = r.trajectory.average
        cx, cy = x0 + 40 + av.valence * (size - 80), y0 + 40 + (1 - av.energy) * (size - 80)
        for k, alpha in ((90, 40), (62, 80), (36, 255)):
            page.draw.ellipse((cx - k, cy - k, cx + k, cy + k), fill=(*LIME, alpha))
        page.text((cx, cy + 105), "YOU", font(False, 30, 800), fill=LIME, anchor="ma")
    labels = font(False, 24, 700)
    page.text((x0 + 20, y0 + 18), "TENSE", labels, alpha=170)
    page.text((x0 + size - 20, y0 + 18), "BRIGHT", labels, anchor="ra", alpha=170)
    page.text((x0 + 20, y0 + size - 44), "LOW", labels, alpha=170)
    page.text((x0 + size - 20, y0 + size - 44), "CALM", labels, anchor="ra", alpha=170)
    page.text(
        (W / 2, y0 + size + 50),
        f"From where your {len(r.moods)} moods sat on Muse's mood map",
        font(False, 30, 500),
        anchor="ma",
        alpha=190,
    )


def _journey(page: Page, r: Rewind) -> None:
    page.blobs(SUN, 2, 90)
    page.chrome(r.period)
    page.kicker(260, "YOUR MOOD JOURNEY")
    y = page.paragraph(PAD, 380, r.journey or "", font(True, 72, 800), W - 2 * PAD)
    size = W - 2 * PAD
    top = int(max(y + 40, 640))
    _mood_map(page, PAD, top, size, r)
    chips = []
    if r.trajectory and r.trajectory.brightness:
        chips.append(
            {
                "lighter": "Getting lighter",
                "heavier": "A little heavier lately",
                "steady": "Holding steady",
            }[r.trajectory.brightness]
        )
    if r.trajectory and r.trajectory.energy and r.trajectory.energy != "steady":
        chips.append(
            {"more energetic": "More energy", "calmer": "Winding down"}[r.trajectory.energy]
        )
    chips.append(f"{len(r.moods)} moods")
    page.pills(top + size + 50, chips, (TANGERINE, VIOLET, PINK))


def _golden_hour(page: Page, r: Rewind) -> None:
    page.blobs(CREAM, 3, 80)
    page.chrome(r.period)
    page.kicker(260, "WHEN YOU SHINE")
    y = 380.0
    for line in wrap(f"{r.golden_hour} are your golden hour.", font(True, 124, 900), W - 2 * PAD):
        page.text((PAD, y), line, font(True, 124, 900))
        y += 132
    # bars: how bright each part of the day felt
    parts = ["morning", "afternoon", "evening", "night"]
    bar_w, gap = 190, (W - 2 * PAD - 4 * 190) / 3
    base = 1560
    best = max(r.day_parts, key=lambda part: r.day_parts[part]) if r.day_parts else None
    for i, part in enumerate(parts):
        x = PAD + i * (bar_w + gap)
        value = r.day_parts.get(part)
        height = 120 + 560 * value if value is not None else 70
        colour = _mood_colour(value) if value is not None else (*BLACK,)
        alpha = 255 if value is not None else 40
        page.draw.rounded_rectangle(
            (x, base - height, x + bar_w, base), radius=36, fill=(*colour, alpha)
        )
        if part == best:
            page.draw.rounded_rectangle(
                (x - 10, base - height - 10, x + bar_w + 10, base + 10),
                radius=44,
                outline=(*BLACK, 255),
                width=6,
            )
        label = "-" if value is None else f"{round(value * 100)}%"
        page.text((x + bar_w / 2, base - height - 30), label, font(False, 40, 800), anchor="md")
        page.text((x + bar_w / 2, base + 30), part.upper(), font(False, 26, 800), anchor="ma")
    page.text(
        (PAD, base + 110),
        "How positive your moods were at each time of day",
        font(False, 30, 500),
        alpha=190,
    )


def _sound(page: Page, r: Rewind) -> None:
    page.blobs(PINK, 2, 80)
    page.chrome(r.period)
    page.kicker(260, "YOUR SOUND")
    dna = r.dna
    if dna is None:
        return
    y = 400.0
    artists = [safe(a) for a in dna.top_artists if safe(a)][:5]
    if artists:
        page.text((PAD, y), "TOP ARTISTS", font(False, 32, 800), fill=LIME, spacing=3)
        y += 70
        for i, artist in enumerate(artists, start=1):
            page.text((PAD, y), str(i), font(True, 104, 900), fill=LIME)
            name_font = fitted(artist, False, 800, 68, W - 2 * PAD - 120, 34)
            page.text((PAD + 120, y + 52), artist, name_font, anchor="lm")
            y += 128
    genres = [safe(g.name) for g in dna.genres if safe(g.name)][:6]
    if genres:
        page.text((PAD, y + 40), "TOP GENRES", font(False, 32, 800), fill=LIME, spacing=3)
        y = page.pills(y + 110, genres, (LIME, SUN, PINK, CREAM), 42)
    footer = []
    if dna.mood_centre:
        footer.append(f"Your taste runs {dna.mood_centre.label}.")
    languages = [safe(lang.name) for lang in dna.languages if safe(lang.name)]
    if languages:
        footer.append("You listen in " + " & ".join(languages[:3]) + ".")
    if footer:
        page.paragraph(PAD, max(y + 70, 1500), " ".join(footer), font(True, 56, 700), W - 2 * PAD)


def _match(page: Page, r: Rewind) -> None:
    page.blobs(CREAM, 3, 90)
    page.chrome(r.period)
    page.kicker(260, "TASTE × MOOD")
    page.text((PAD - 8, 360), f"{r.match}%", font(True, 300, 900), fill=VIOLET)
    page.text((PAD, 700), "match between your music and your moods", font(False, 40, 700))
    size = 640
    x0, y0 = (W - size) // 2, 820
    page.draw.rounded_rectangle((x0, y0, x0 + size, y0 + size), radius=44, fill=(*BLACK, 18))
    page.draw.line((x0 + size / 2, y0, x0 + size / 2, y0 + size), fill=(*BLACK, 60), width=3)
    page.draw.line((x0, y0 + size / 2, x0 + size, y0 + size / 2), fill=(*BLACK, 60), width=3)

    def at(v: float, e: float) -> tuple[float, float]:
        return x0 + 50 + v * (size - 100), y0 + 50 + (1 - e) * (size - 100)

    if not (r.dna and r.dna.mood_centre and r.trajectory and r.trajectory.average):
        return
    tx, ty = at(r.dna.mood_centre.valence, r.dna.mood_centre.energy)
    mx, my = at(r.trajectory.average.valence, r.trajectory.average.energy)
    steps = 14
    for k in range(steps):  # dashed line between the two
        if k % 2 == 0:
            a, b = k / steps, (k + 1) / steps
            page.draw.line(
                (tx + (mx - tx) * a, ty + (my - ty) * a, tx + (mx - tx) * b, ty + (my - ty) * b),
                fill=(*BLACK, 255),
                width=6,
            )
    page.draw.rounded_rectangle(
        (tx - 34, ty - 34, tx + 34, ty + 34), radius=10, fill=(*VIOLET, 255)
    )
    page.draw.ellipse(
        (mx - 36, my - 36, mx + 36, my + 36), fill=(*TANGERINE, 255), outline=(*CREAM, 255), width=5
    )
    label = font(False, 26, 800)
    taste_below = ty >= my  # the lower dot gets its label below, the higher one above
    page.text(
        (tx, ty + 50 if taste_below else ty - 50),
        "YOUR TASTE",
        label,
        anchor="ma" if taste_below else "md",
    )
    page.text(
        (mx, my - 52 if taste_below else my + 52),
        "YOUR MOODS",
        label,
        anchor="md" if taste_below else "ma",
    )
    page.paragraph(PAD, y0 + size + 70, r.match_line or "", font(True, 54, 700), W - 2 * PAD)


def _learned(page: Page, r: Rewind) -> None:
    page.blobs(SUN, 2, 70)
    page.chrome(r.period)
    page.kicker(260, "WHAT MUSE LEARNED")
    learned = r.learned
    if learned is None:
        return
    half = (W - 2 * PAD - 40) / 2
    for i, (value, label, colour) in enumerate(
        ((learned.likes, "THUMBS UP", SUN), (learned.dislikes, "THUMBS DOWN", BLACK))
    ):
        x = PAD + i * (half + 40)
        page.draw.rounded_rectangle((x, 380, x + half, 760), radius=48, fill=(*colour, 255))
        fg = BLACK if colour == SUN else CREAM
        page.text((x + half / 2, 520), str(value), font(True, 200, 900), fill=fg, anchor="mm")
        page.text((x + half / 2, 690), label, font(False, 32, 800), fill=fg, anchor="mm")
    if learned.dislikes == 0:
        line = "Not a single thumbs down. Easy to please."
    elif learned.likes >= 3 * learned.dislikes:
        line = "You know what you like, and Muse is listening."
    else:
        line = "Picky? Good. Every thumbs down made the next mix sharper."
    y = page.paragraph(PAD, 830, line, font(True, 62, 800), W - 2 * PAD)
    loved = [safe(a.name) for a in learned.liked_artists if safe(a.name)]
    if loved:
        page.text(
            (PAD, y + 70), "YOUR MOST-LOVED ARTIST", font(False, 32, 800), fill=SUN, spacing=3
        )
        page.text((PAD, y + 130), loved[0], fitted(loved[0], True, 900, 130, W - 2 * PAD))
        if len(loved) > 1:
            page.text(
                (PAD, y + 340), "MUSE WILL BRING MORE OF", font(False, 32, 800), fill=SUN, spacing=3
            )
            page.pills(y + 400, loved[1:6], (SUN, CREAM, VIOLET, BLACK), 40)
    page.squiggle(SUN, H - 330, 34, 14)
    page.dots(CREAM, W - PAD - 170, H - 260, 6, 2)


def _playlists(page: Page, r: Rewind) -> None:
    page.blobs(LIME, 2, 60)
    page.chrome(r.period)
    page.kicker(260, "YOUR PLAYLISTS")
    count = len(r.playlists)
    page.text((PAD - 6, 360), str(count), font(True, 260, 900), fill=SUN)
    word = "playlist" if count == 1 else "playlists"
    page.text((PAD, 650), f"{word} made with Muse and saved to Spotify", font(False, 40, 700))
    y = 770
    for i, playlist in enumerate(r.playlists[:6]):
        colour = TILE_COLOURS[i % len(TILE_COLOURS)]
        page.draw.rounded_rectangle((PAD, y, W - PAD, y + 140), radius=36, fill=(*CREAM, 255))
        page.draw.rounded_rectangle(
            (PAD + 20, y + 20, PAD + 120, y + 120), radius=22, fill=(*colour, 255)
        )
        _record_mark(page.draw, PAD + 70, y + 70, 30, CREAM)
        name = safe(playlist.name) or "Muse playlist"
        page.text(
            (PAD + 150, y + 30),
            name,
            fitted(name, False, 800, 44, W - 2 * PAD - 190, 28),
            fill=BLACK,
        )
        when = playlist.created_at
        page.text(
            (PAD + 150, y + 90),
            f"{playlist.track_count} songs  ·  {when.day} {when:%b}",
            font(False, 30, 500),
            fill=BLACK,
            alpha=170,
        )
        y += 164
    if count > 6:
        page.text((PAD, y + 10), f"and {count - 6} more", font(False, 36, 700))


def _outro(page: Page, r: Rewind) -> None:
    page.chrome(r.period)
    page.kicker(260, f"THAT'S YOUR {r.span.upper()}")
    title = safe(f"{r.title_owner} Muse Rewind")
    y = 380.0
    for line in wrap(title, font(True, 120, 900), W - 2 * PAD):
        page.text((PAD, y), line, font(True, 120, 900), fill=TANGERINE)
        y += 128
    tiles: list[tuple[str, str]] = []
    if r.moods_included:
        tiles.append(("Moods logged", str(len(r.moods))))
    if r.top_mood:
        tiles.append((f"Mood of the {r.span}", safe(r.top_mood).capitalize()))
    if r.personality:
        tiles.append(("Personality", r.personality.name.removeprefix("The ")))
    if r.dna and r.dna.top_artists and safe(r.dna.top_artists[0]):
        tiles.append(("Top artist", safe(r.dna.top_artists[0])))
    if r.learned:
        tiles.append(("Songs rated", str(r.rated)))
    tiles.append(("Playlists made", str(len(r.playlists))))
    tiles = tiles[:6]
    col_w = (W - 2 * PAD - 30) / 2
    top = y + 50
    for i, (label, value) in enumerate(tiles):
        x = PAD + (i % 2) * (col_w + 30)
        ty = top + (i // 2) * 290
        colour = TILE_COLOURS[i % len(TILE_COLOURS)]
        fg = BLACK if colour in (LIME, SUN, PINK) else CREAM
        page.draw.rounded_rectangle((x, ty, x + col_w, ty + 260), radius=40, fill=(*colour, 255))
        page.text((x + 36, ty + 36), label.upper(), font(False, 26, 800), fill=fg, spacing=2)
        page.text(
            (x + 36, ty + 120), value, fitted(value, True, 900, 96, int(col_w) - 72, 36), fill=fg
        )
    bottom = top + ((len(tiles) + 1) // 2) * 290 + 40
    page.paragraph(
        PAD,
        max(bottom, 1560),
        "Made with Muse: mood-aware playlists from what you like and how you feel. "
        "Muse keeps no copy of this report. A playful look at moods you chose, not a diagnosis.",
        font(False, 32, 500),
        W - 2 * PAD,
        alpha=200,
    )


PAGES: dict[str, Callable[[Page, Rewind], None]] = {
    "cover": _cover,
    "mood_word": _mood_word,
    "personality": _personality,
    "journey": _journey,
    "golden_hour": _golden_hour,
    "sound": _sound,
    "match": _match,
    "learned": _learned,
    "playlists": _playlists,
    "outro": _outro,
}


def render_pages(r: Rewind) -> list[Image.Image]:
    kinds = r.pages
    seed = sum(ord(c) for c in (r.first_name or "")) + r.days
    images = []
    for number, kind in enumerate(kinds, start=1):
        page = Page(kind, number, len(kinds), seed)
        PAGES[kind](page, r)
        images.append(page.finish())
    return images


def rewind_pdf(r: Rewind) -> bytes:
    pages = render_pages(r)
    out = io.BytesIO()
    pages[0].save(
        out,
        "PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=144.0,  # 1080x1920 px -> 7.5 x 13.3 in, a phone-shaped page
        quality=82,
        title="Muse Rewind",
        creator="Muse",
    )
    return out.getvalue()


def rewind_preview(r: Rewind, height: int = 560) -> bytes:
    """All pages side by side, small, as one JPEG (for the website's preview)."""
    pages = render_pages(r)
    width = round(W * height / H)
    gap = 24
    strip = Image.new("RGB", (len(pages) * (width + gap) - gap, height), (255, 255, 255))
    for i, page in enumerate(pages):
        strip.paste(page.resize((width, height), Image.Resampling.LANCZOS), (i * (width + gap), 0))
    out = io.BytesIO()
    strip.save(out, "JPEG", quality=84, optimize=True)
    return out.getvalue()
