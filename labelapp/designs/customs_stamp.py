"""Customs Stamp: passport visa page; origin in a rotated double-ring entry stamp, dose in a box stamp."""
import math
from .common import *

NAME = "Customs Stamp"
ORDER = 11


_M = ImageDraw.Draw(Image.new("1", (1, 1)))    # measuring context


def _curved(hs, text, c, r, f, bottom=False):
    """Text set along a circle of radius r around (c, c) on a HiRes canvas, centred at the top
    (reading clockwise) or the bottom (reading left-to-right, glyph tops toward the centre)."""
    widths = [_M.textlength(ch, font=f) for ch in text]
    sc = hs.s
    R = r * sc
    span = sum(widths) / R
    a = (math.pi + span / 2) if bottom else -span / 2
    for ch, w in zip(text, widths):
        step = w / R
        mid = a - step / 2 if bottom else a + step / 2
        x = c * sc + R * math.sin(mid)
        y = c * sc - R * math.cos(mid)
        g = Image.new("L", (int(w) + 10, int(f.size * 1.3)), 0)
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), ch, font=f, fill=255, anchor="mm")
        g = g.rotate(-math.degrees(mid - (math.pi if bottom else 0)), resample=Image.BICUBIC, expand=True)
        hs.im.paste(0, (int(x - g.width / 2), int(y - g.height / 2)), g)
        a = a - step if bottom else a + step


def _entry_stamp(data, size=236):
    """Round entry stamp: double ring, curved legend, origin + entry date in the middle."""
    hs = HiRes(size, size)
    d, s = hs.d, hs.s
    c = size / 2
    r_out, r_in = c - 6, c - 38
    for r, w in ((r_out, 3), (r_out - 6, 2), (r_in, 3)):
        d.ellipse(hs.p(c - r, c - r, c + r, c + r), outline=0, width=w * s)
    band = (r_out - 6 + r_in) / 2
    lf = hs.font("bold", 16)
    _curved(hs, "VACUUM SEALED", c, band, lf)
    _curved(hs, "SINGLE DOSE", c, band, lf, bottom=True)
    for ang in (-math.pi / 2, math.pi / 2):          # star separators at 9 and 3 o'clock
        x, y = c + band * math.sin(ang), c - band * math.cos(ang)
        d.ellipse(hs.p(x - 4, y - 4, x + 4, y + 4), fill=0)

    inner = (r_in - 6) * 2
    origin = (val(data, "origin") or val(data, "region") or "Coffee").upper()
    of, short = fit_line(_M, origin, inner - 16, 34, style="condensed")
    if short != origin and len(origin.split()[-1]) >= 4:      # 'DEMOCRATIC REPUBLIC OF THE CONGO' -> 'CONGO'
        of, short = fit_line(_M, origin.split()[-1], inner - 16, 34, style="condensed")
    origin = short
    seal = val(data, "seal_date").upper()
    df, seal = fit_line(_M, seal, inner - 30, 22, style="condensed")   # condensed: full date at >= 18 px
    d.text((c * s, (c - 16) * s), "ENTRY", font=hs.font("bold", 16), fill=0, anchor="ms")
    d.text((c * s, (c + 14) * s), origin, font=hs.font("condensed", of.size), fill=0, anchor="ms")
    d.text((c * s, (c + 22) * s), seal, font=hs.font("condensed", df.size), fill=0, anchor="ma")
    return hs.to_1bit(angle=9)


def _dose_stamp(dose, w=168, h=124):
    """Rectangular double-border 'admitted' stamp holding the dose."""
    hs = HiRes(w, h)
    d, s = hs.d, hs.s
    d.rectangle(hs.p(6, 6, w - 6, h - 6), outline=0, width=3 * s)
    d.rectangle(hs.p(12, 12, w - 12, h - 12), outline=0, width=2 * s)
    d.text((w / 2 * s, 22 * s), "ADMITTED · DOSE", font=hs.font("bold", 15), fill=0, anchor="ma")
    if dose:
        gf, _ = fit_line(_M, dose_measure(dose) + " g", w - 40, 64, 30, "condensed")
        f = hs.font("condensed", gf.size)
        x = w / 2 * s - d.textlength(dose_measure(dose) + " g", font=f) / 2
        base = (h - 22) * s
        draw_dose(d, (x, base), dose, f, anchor="ls")
        d.text((x + d.textlength(dose_measure(dose) + " ", font=f), base), "g", font=f, fill=0, anchor="ls")
    return hs.to_1bit(angle=-6)


def _caption(d, x, y, text):
    d.text((x, y), text.upper(), font=face("bold", MIN_CAPTION_PX), fill=BLACK)


def _field(d, x, y, label, value, maxw, size=24, lines=1, max_h=None):
    _caption(d, x, y + 1, label)
    if lines == 1:            # one-line slot: shorten a parenthetical before ellipsizing
        f, v = fit_short(d, value, maxw, size)
        ls, lh = [v], int(f.size * 1.12)
    else:
        f, ls, lh = fit_block_face(d, value, maxw, max_h or int(size * 1.12) * lines, size, MIN_PX, "bold",
                                   leading=1.12, max_lines=lines)
    return draw_lines(d, x, y + 19, ls, f, lh) + 8


def _mrz(data, dose, n=30):
    def clean(s):
        import unicodedata
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return "".join(c if c.isalnum() else "<" for c in s.upper())
    name = clean(val(data, "coffee_name") or "COFFEE")
    l1 = ("P<VAC" + clean(origin_code(data)) + "<" + name + "<" * n)[:n]
    l2 = (clean(f"{dose}G") + "<" + batch_code(data) + "<" + clean(val(data, "process") or "BEANS") + "<" * n)[:n]
    return l1, l2


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw = R - L
    dose = fmt_dose(data)

    # header
    hf = face("bold", 22)
    spaced(d, "COFFEE PASSPORT", L, MARGIN, hf, spacing=3)
    nf = face("mono_bold", 18)
    d.text((R, MARGIN + 18), f"№{batch_code(data)}", font=nf, fill=BLACK, anchor="rs")
    y = MARGIN + 32
    hr(d, y, w=3); y += 3
    hr(d, y + 3, w=1 + 1); y += 14

    # identity fields
    pairs = [("Issued by", val(data, "roaster")),
             ("Place of birth", join(val(data, "region"), val(data, "producer"), sep=", ")),
             ("Process", val(data, "process")), ("Variety", val(data, "variety")),
             ("Elevation", val(data, "altitude"))]
    pairs = [(k, v) for k, v in pairs if v]
    sparse = len(pairs) <= 1                 # nothing else above the stamps: a long name may take 5 lines
    y = _field(d, L, y, "Name / Nom", val(data, "coffee_name") or "Coffee", mw, size=26,
               lines=5 if sparse else 3, max_h=150 if sparse else 60 if len(pairs) > 3 else 90)
    stamp_top_min = 300
    # two columns for the short ones, full width for the long ones
    full = [p for p in pairs if p[0] in ("Issued by", "Place of birth")]
    half = [p for p in pairs if p not in full]
    for k, v in full:
        if y + 46 > stamp_top_min:
            break
        y = _field(d, L, y, k, v, mw, size=22)
    colw = (mw - 16) // 2
    for i in range(0, len(half), 2):
        if y + 46 > stamp_top_min + 10:
            break
        row = half[i:i + 2]
        ys = [_field(d, L + j * (colw + 16), y, k, v, colw, size=22) for j, (k, v) in enumerate(row)]
        y = max(ys)

    # stamps
    mrz_top = H - MARGIN - 50
    area_top = max(y + 2, 280)
    area_h = mrz_top - 10 - area_top
    es = _entry_stamp(data, size=max(180, min(222, area_h)))
    paste_ink(im, es, L - 8, area_top + (area_h - es.height) // 2)
    ds = _dose_stamp(dose_text(data))
    paste_ink(im, ds, R - ds.width + 6, mrz_top - 6 - ds.height)

    # tasting notes as a handwritten-ish visa remark, top right of stamp area
    notes = val(data, "notes")
    if notes:
        nx = L + es.width - 4
        nw = R - nx
        avail = (mrz_top - 10 - ds.height) - area_top - 8
        if nw > 100 and avail > 40:
            _caption(d, nx, area_top + 5, "Remarks")
            f3, ls, lh3 = fit_block_face(d, notes, nw, avail - 22, 20, MIN_PX, "oblique", leading=1.15)
            draw_lines(d, nx, area_top + 24, ls, f3, lh3)

    # machine-readable zone (decorative)
    hr(d, mrz_top, w=2)
    mf = face("mono_bold", 20)
    l1, l2 = _mrz(data, dose)
    n = 30
    while tw(d, l1[:n], mf) > mw and n > 10:
        n -= 1
    d.text((L, mrz_top + 8), l1[:n], font=mf, fill=BLACK)
    d.text((L, mrz_top + 30), l2[:n], font=mf, fill=BLACK)
    return finish(im)
