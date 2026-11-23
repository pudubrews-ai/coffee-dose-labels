"""Shared helpers for label designs. All drawing is strictly 1-bit (no anti-aliasing)."""
import math
from datetime import date
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont

W, H = 400, 640
MARGIN = 24                      # ~3 mm safe margin
FONT_FILE = "/System/Library/Fonts/Helvetica.ttc"
FALLBACKS = ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"]
BLACK, WHITE = 0, 1

# Legibility floors for 203 dpi thermal paper (font size in px; 8 px = 1 mm).
# Any text that carries information is never set below MIN_PX: when it doesn't fit at the floor it
# wraps (within the design's line budget), then ellipsizes, or the design drops the field entirely.
# Short bold caption labels ("SEALED", "Name / Nom") may go down to MIN_CAPTION_PX.
# Purely decorative strings (MRZ, barcode digits) are exempt but still drawn crisp, never under 15.
MIN_PX = 18
MIN_CAPTION_PX = 15
DOSE_PLACEHOLDER = "\u2014"      # sentinel for "no dose yet"; never drawn as a glyph (see draw_dose)
DOSE_SAMPLE = "18"               # the blank dose is laid out as if it were this number

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
    """'17.5', '18' (never '18.0'); accepts a decimal comma. '' unless 0 < dose <= 1000 g."""
    try:
        g = float(str(data.get("dose")).strip().replace(",", "."))
    except (TypeError, ValueError):
        return ""
    if not (math.isfinite(g) and 0 < g <= 1000):
        return ""
    return f"{round(g, 2):g}"


def dose_text(data: dict) -> str:
    """Dose for display: the number, or DOSE_PLACEHOLDER (drawn by draw_dose as a light blank)."""
    return fmt_dose(data) or DOSE_PLACEHOLDER


def dose_measure(dose: str) -> str:
    """The string to measure/fit the dose with: the blank is sized like DOSE_SAMPLE."""
    return DOSE_SAMPLE if dose == DOSE_PLACEHOLDER else dose


def dose_w(d, dose, f) -> float:
    return tw(d, dose_measure(dose), f)


def draw_dose(d, xy, dose, f, anchor="la"):
    """Draw the dose number. With no dose yet, draw a light dashed fill-in rule exactly where the
    digits of DOSE_SAMPLE would sit (on their baseline), so a unit placed after dose_w() lines up
    as it will on the printed label, without a heavy black bar."""
    if dose != DOSE_PLACEHOLDER:
        d.text(xy, dose, font=f, fill=BLACK, anchor=anchor)
        return
    x0, _, x1, y1 = d.textbbox(xy, DOSE_SAMPLE, font=f, anchor=anchor)
    t = max(2, round(f.size / 48))
    dashed_h(d, y1 - t, x0, x1, dash=max(6, round(f.size / 7)), gap=max(4, round(f.size / 12)), w=t)


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


def fit_size(d, text, maxw, start, minimum=MIN_PX, bold=True) -> int:
    minimum = max(minimum, MIN_PX)
    start = max(start, minimum)
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
    if max_lines is not None and len(lines) > max(1, int(max_lines)):
        max_lines = max(1, int(max_lines))
        keep = lines[:max_lines]
        keep[-1] = ellipsize(d, keep[-1] + " " + " ".join(lines[max_lines:]), f, maxw)
        lines = keep
    return lines


def fit_block(d, text, maxw, max_h, start, minimum=MIN_PX, bold=True, leading=1.15, max_lines=None):
    """Largest font size (start..minimum) whose wrapped text fits max_h; returns (font, lines, line_h).
    At the minimum size (never below MIN_PX), truncates with an ellipsis instead of overflowing."""
    minimum = max(minimum, MIN_PX)
    start = max(start, minimum)
    for s in range(start, minimum - 1, -1):
        f = font(s, bold)
        lh = int(s * leading)
        lines = wrap(d, text, f, maxw)
        if (not max_lines or len(lines) <= max_lines) and len(lines) * lh <= max_h:
            return f, lines, lh
    f = font(minimum, bold)
    lh = int(minimum * leading)
    n = max(1, int(max_h // lh))
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


def ellipsize_spaced(d, text, f, maxw, spacing=2) -> str:
    """ellipsize() for spaced(): accounts for the extra letter spacing."""
    def width(t):
        return sum(tw(d, c, f) + spacing for c in t) - spacing
    if width(text) <= maxw:
        return text
    while text and width(text.rstrip() + "…") > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def fit_spaced(d, text, maxw, start, spacing=2, max_lines=2, style="bold"):
    """Letter-spaced caps line for a roaster name: the largest size start..MIN_PX that fits one line;
    then tighter letter spacing at MIN_PX; then up to max_lines wrapped lines (last one ellipsized).
    Returns (font, lines, spacing). Draw each line with spaced()."""
    def width(t, f, sp):
        return sum(tw(d, c, f) + sp for c in t) - sp
    for s in range(max(start, MIN_PX), MIN_PX - 1, -1):
        f = face(style, s)
        if width(text, f, spacing) <= maxw:
            return f, [text], spacing
    f = face(style, MIN_PX)
    for sp in range(spacing - 1, -1, -1):
        if width(text, f, sp) <= maxw:
            return f, [text], sp
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if not cur or width(t, f, spacing) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [" ".join(lines[max_lines - 1:])]
    return f, [ellipsize_spaced(d, ln, f, maxw, spacing) for ln in lines], spacing


def hr(d, y, x0=MARGIN, x1=W - MARGIN, w=2):
    d.rectangle([x0, y, x1, y + w - 1], fill=BLACK)


def finish(im):
    assert im.mode == "1" and im.size == (W, H)
    return im


# ---------------------------------------------------------------------------
# Extra helpers for the more decorative designs (all output stays strictly 1-bit).

_FACES = {   # style -> (file, index); falls back to Helvetica Bold/Regular
    "regular": ("/System/Library/Fonts/Helvetica.ttc", 0),
    "bold": ("/System/Library/Fonts/Helvetica.ttc", 1),
    "oblique": ("/System/Library/Fonts/Helvetica.ttc", 2),
    "bold_oblique": ("/System/Library/Fonts/Helvetica.ttc", 3),
    "medium": ("/System/Library/Fonts/HelveticaNeue.ttc", 10),
    "condensed": ("/System/Library/Fonts/HelveticaNeue.ttc", 4),       # Condensed Bold
    "condensed_black": ("/System/Library/Fonts/HelveticaNeue.ttc", 9),
    "mono": ("/System/Library/Fonts/Menlo.ttc", 0),
    "mono_bold": ("/System/Library/Fonts/Menlo.ttc", 1),
}


@lru_cache(maxsize=512)
def face(style: str, size: int) -> ImageFont.FreeTypeFont:
    """Named typeface ('bold', 'regular', 'condensed', 'mono_bold', ...) with Helvetica fallback."""
    path, idx = _FACES.get(style, _FACES["bold"])
    if size == 20 and idx == 1 and path.endswith("Helvetica.ttc"):
        size = 20.5          # Helvetica Bold's 1-bit hinting fuses the i-dot into the stem at exactly 20 px
    try:
        return ImageFont.truetype(path, size, index=idx)
    except OSError:
        return font(size, bold=style not in ("regular", "oblique", "mono"))


def fit_line(d, text, maxw, start, minimum=MIN_PX, style="bold"):
    """Largest face(style) size in start..minimum fitting maxw on one line; ellipsizes at minimum
    (never below MIN_PX). Returns (font, text)."""
    minimum = max(minimum, MIN_PX)
    start = max(start, minimum)
    for s in range(start, minimum - 1, -1):
        f = face(style, s)
        if tw(d, text, f) <= maxw:
            return f, text
    f = face(style, minimum)
    return f, ellipsize(d, text, f, maxw)


def fit_block_face(d, text, maxw, max_h, start, minimum=MIN_PX, style="bold", leading=1.15, max_lines=None):
    """fit_block() for any face(style), floored at MIN_PX. Returns (font, lines, line_h)."""
    minimum = max(minimum, MIN_PX)
    start = max(start, minimum)
    for s in range(start, minimum - 1, -1):
        f = face(style, s)
        lh = int(s * leading)
        lines = wrap(d, text, f, maxw)
        if (not max_lines or len(lines) <= max_lines) and len(lines) * lh <= max_h:
            return f, lines, lh
    f = face(style, minimum)
    lh = int(minimum * leading)
    n = max(1, int(max_h // lh))
    if max_lines:
        n = min(n, max_lines)
    return f, wrap(d, text, f, maxw, max_lines=n), lh


def fits_block_face(d, text, maxw, max_lines, size=MIN_PX, style="bold") -> bool:
    """True if text wraps into at most max_lines at this size (no ellipsis needed)."""
    return len(wrap(d, text, face(style, max(size, MIN_PX)), maxw)) <= max_lines


def short_forms(text: str) -> list[str]:
    """Progressively shorter forms of a value with a parenthetical, most informative first:
    'Washed (TyOxy: oxidation, 48h dry...)' -> 'Washed (TyOxy)' -> 'Washed'."""
    import re
    forms = [text]
    m = re.search(r"\s*\(([^)]*)\)?", text)
    if m and m.start() > 0:
        head = re.split(r"[:;]|,(?!\d)", m.group(1))[0].strip()
        if head and head != m.group(1).strip():
            forms.append(f"{text[:m.start()]} ({head})")
        forms.append(text[:m.start()].strip())
    return forms


def fit_short(d, text, maxw, start, minimum=MIN_PX, style="bold"):
    """fit_line() that, rather than ellipsizing at the floor, first tries short_forms() of the text.
    Returns (font, text)."""
    for t in short_forms(text):
        f, out = fit_line(d, t, maxw, start, minimum, style)
        if out == t:
            return f, t
    return fit_line(d, short_forms(text)[-1], maxw, start, minimum, style)


def fit_parts(d, parts, maxw, max_lines, size=MIN_PX, style="regular", sep=" · "):
    """Join (text, priority) parts so they wrap into max_lines at `size` (>= MIN_PX): first shorten
    parentheticals, then drop the lowest-priority parts (highest number). Returns the joined string
    (the caller still ellipsizes if even the top-priority part alone is too long)."""
    parts = [(t, p) for t, p in parts if t]
    while parts:
        n = max(len(short_forms(t)) for t, _ in parts)
        for i in range(n):
            text = sep.join(short_forms(t)[min(i, len(short_forms(t)) - 1)] for t, _ in parts)
            if fits_block_face(d, text, maxw, max_lines, size, style):
                return text
        if len(parts) == 1:
            return text
        worst = max(p for _, p in parts)
        parts = [(t, p) for t, p in parts if p != worst] or parts[:1]
    return ""


def ink_h(d, text, f) -> int:
    """Height of the inked glyphs above the baseline (cap height for caps/digits)."""
    bb = d.textbbox((0, 0), text, font=f, anchor="ls")
    return -bb[1]


def dashed_h(d, y, x0, x1, dash=8, gap=6, w=2):
    x, x1, y = round(x0), round(x1), round(y)
    while x < x1:
        d.rectangle([x, y, min(x + dash, x1) - 1, y + w - 1], fill=BLACK)
        x += dash + gap


def dashed_v(d, x, y0, y1, dash=8, gap=6, w=2):
    y, y1, x = round(y0), round(y1), round(x)
    while y < y1:
        d.rectangle([x, y, x + w - 1, min(y + dash, y1) - 1], fill=BLACK)
        y += dash + gap


def ring(d, cx, cy, r, w=2):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=w)


_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def parse_date(s):
    """'23 Nov 2026', '2026-11-23', '23/11/2026', '23.11.2026', 'November 23, 2026',
    'Roasted on the 23rd of November 2026' -> date, else None (e.g. no year given)."""
    import re
    from datetime import datetime
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d %B %Y", "%d/%m/%Y", "%d.%m.%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    low = t.lower()
    y = re.findall(r"\b(20\d\d)\b", low)
    m = re.findall(r"\b(" + "|".join(_MONTHS) + r")[a-z]*\.?(?=[\s,\d]|$)", low)
    rest = re.sub(r"\b20\d\d\b", " ", low)
    dd = re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", rest)
    if len(y) == 1 and len(m) == 1 and len(dd) == 1:
        try:
            return date(int(y[0]), _MONTHS.index(m[0]) + 1, int(dd[0]))
        except ValueError:
            return None
    return None


def normalize(data: dict) -> dict:
    """Copy of the label data with seal / roast dates in one style ('30 Nov 2026') when they parse
    (ISO, 30/11/2026, 'Roasted on the 30th of November 2026'); anything else is left as written."""
    out = dict(data)
    for k in ("seal_date", "roast_date"):
        dt = parse_date(val(out, k))
        if dt:
            out[k] = fmt_date(dt)
    return out


def batch_code(data: dict) -> str:
    """Short batch number derived from the seal date, e.g. '261123' (or digits of the raw string)."""
    s = val(data, "seal_date")
    dt = parse_date(s)
    if dt:
        return dt.strftime("%y%m%d")
    return "".join(c for c in s if c.isdigit())[-6:]


def origin_code(data: dict) -> str:
    """Three-letter pseudo airport code from origin (or region / coffee name)."""
    for k in ("origin", "region", "coffee_name"):
        letters = "".join(c for c in val(data, k).upper() if c.isalpha())
        if len(letters) >= 3:
            return letters[:3]
    return "BNS"


def notes_list(data: dict, max_items=None) -> list[str]:
    """Tasting notes split on commas / ' and ' / '&' into tidy capitalised items."""
    import re
    raw = val(data, "notes")
    if not raw:
        return []
    parts = [p.strip(" .;") for p in re.split(r",|;|/|\s&\s|\band\b|\bwith\b", raw)]
    items = [p[:1].upper() + p[1:] for p in parts if p]
    return items[:max_items] if max_items else items


def paste_ink(im, layer, x, y):
    """Paste the black pixels of a 1-bit layer onto im at (x, y) (white stays transparent)."""
    mask = layer.point(lambda v: 255 if v == 0 else 0, mode="L")
    im.paste(BLACK, (int(x), int(y), int(x) + layer.width, int(y) + layer.height), mask)


def text_layer(text, f, pad=2, outline=0):
    """Text rendered alone on a tight 1-bit layer (rotate it with Image.transpose, losslessly).
    outline=n draws n-px outlined letters instead of solid ones."""
    tmp = ImageDraw.Draw(Image.new("1", (1, 1)))
    bb = tmp.textbbox((0, 0), text, font=f, stroke_width=outline)
    lay = Image.new("1", (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), WHITE)
    ld = ImageDraw.Draw(lay)
    ld.fontmode = "1"
    ld.text((pad - bb[0], pad - bb[1]), text, font=f, fill=WHITE if outline else BLACK,
            stroke_width=outline, stroke_fill=BLACK)
    return lay


class HiRes:
    """Scratch canvas drawn at `scale`x in greyscale, then rotated and thresholded back to crisp 1-bit.
    Used for rotated stamps: thresholding (no dithering) gives clean edges at any angle."""

    def __init__(self, w, h, scale=3):
        self.s, self.w, self.h = scale, w, h
        self.im = Image.new("L", (w * scale, h * scale), 255)
        self.d = ImageDraw.Draw(self.im)

    def font(self, style, size):
        return face(style, size * self.s)

    def p(self, *v):
        return [c * self.s for c in v]

    def to_1bit(self, angle=0.0, threshold=150):
        im = self.im
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, fillcolor=255)
        im = im.resize((self.w, self.h), Image.LANCZOS)
        return im.point(lambda v: 255 if v >= threshold else 0).convert("1", dither=Image.Dither.NONE)


def fake_barcode(d, x0, y0, x1, y1, seed="dose"):
    """Decorative, non-scannable bar pattern (no real symbology) between x0..x1."""
    import random
    rnd = random.Random(seed)
    x = x0
    while x < x1:
        bw = rnd.choice((2, 2, 3, 4, 6))
        if x + bw > x1:
            break
        d.rectangle([x, y0, x + bw - 1, y1], fill=BLACK)
        x += bw + rnd.choice((2, 3, 3, 4, 6))
