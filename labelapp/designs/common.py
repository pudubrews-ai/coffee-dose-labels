"""Shared helpers for label designs. All drawing is strictly 1-bit (no anti-aliasing)."""
from datetime import date
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

W, H = 400, 640
MARGIN = 24                      # ~3 mm safe margin
FONT_FILE = "/System/Library/Fonts/Helvetica.ttc"
FALLBACKS = ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"]
BLACK, WHITE = 0, 1

FIELDS = ["roaster", "coffee_name", "origin", "region", "producer", "process",
          "variety", "altitude", "notes", "roast_date", "source_url"]


@lru_cache(maxsize=256)
def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for path in [FONT_FILE] + FALLBACKS:
        try:
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size, index=1 if bold else 0)
            return ImageFont.truetype(path.replace("Arial.ttf", "Arial Bold.ttf") if bold else path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def new_canvas():
    im = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"             # no anti-aliasing
    return im, d


def val(data: dict, key: str) -> str:
    """Stripped value or '' (omit empty fields cleanly)."""
    v = data.get(key)
    if v is None:
        return ""
    v = " ".join(str(v).split())
    return "" if v.lower() in ("none", "null", "n/a", "unknown") else v


def join(*parts, sep=" · ") -> str:
    return sep.join(p for p in parts if p)


def fmt_dose(data: dict) -> str:
    try:
        g = float(data.get("dose"))
    except (TypeError, ValueError):
        return ""
    return f"{g:g}"


def today_str() -> str:
    return fmt_date(date.today())


def fmt_date(d: date) -> str:
    return f"{d.day} {d.strftime('%b %Y')}"


def tw(d, text, f) -> float:
    return d.textlength(text, font=f)


def ellipsize(d, text, f, maxw) -> str:
    if tw(d, text, f) <= maxw:
        return text
    while text and tw(d, text + "…", f) > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def fit_size(d, text, maxw, start, minimum, bold=True) -> int:
    s = start
    while s > minimum and tw(d, text, font(s, bold)) > maxw:
        s -= 1
    return s


def wrap(d, text, f, maxw, max_lines=None) -> list[str]:
    """Greedy word wrap; hard-splits over-long words; ellipsis if lines exceeded."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        while tw(d, w, f) > maxw:           # over-long single word
            k = len(w)
            while k > 1 and tw(d, w[:k], f) > maxw:
                k -= 1
            if cur:
                lines.append(cur); cur = ""
            lines.append(w[:k]); w = w[k:]
        t = f"{cur} {w}".strip()
        if tw(d, t, f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        keep = lines[:max_lines]
        keep[-1] = ellipsize(d, keep[-1] + " " + " ".join(lines[max_lines:]), f, maxw)
        lines = keep
    return lines


def fit_block(d, text, maxw, max_h, start, minimum, bold=True, leading=1.15, max_lines=None):
    """Largest font size (start..minimum) whose wrapped text fits max_h; returns (font, lines, line_h).
    At the minimum size, truncates with an ellipsis instead of overflowing."""
    for s in range(start, minimum - 1, -1):
        f = font(s, bold)
        lh = int(s * leading)
        lines = wrap(d, text, f, maxw)
        if (not max_lines or len(lines) <= max_lines) and len(lines) * lh <= max_h:
            return f, lines, lh
    f = font(minimum, bold)
    lh = int(minimum * leading)
    n = max(1, max_h // lh)
    if max_lines:
        n = min(n, max_lines)
    return f, wrap(d, text, f, maxw, max_lines=n), lh


def draw_lines(d, x, y, lines, f, lh, anchor="l", cx=None):
    for ln in lines:
        xx = x if anchor == "l" else cx - tw(d, ln, f) / 2
        d.text((xx, y), ln, font=f, fill=BLACK)
        y += lh
    return y


def spaced(d, text, x, y, f, spacing=2, center_x=None):
    """Letter-spaced text (for small caps look)."""
    total = sum(tw(d, c, f) + spacing for c in text) - spacing
    if center_x is not None:
        x = center_x - total / 2
    for c in text:
        d.text((x, y), c, font=f, fill=BLACK)
        x += tw(d, c, f) + spacing
    return total


def hr(d, y, x0=MARGIN, x1=W - MARGIN, w=2):
    d.rectangle([x0, y, x1, y + w - 1], fill=BLACK)


def finish(im):
    assert im.mode == "1" and im.size == (W, H)
    return im
