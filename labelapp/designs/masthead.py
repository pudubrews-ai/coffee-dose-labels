"""Masthead: editorial. The origin runs up the left edge in huge outline type; quiet text column."""
from .common import *

NAME = "Masthead"
ORDER = 15


def _vertical_word(im, d, word, x, top, bottom, max_w):
    """Origin word reading bottom-to-top, as large as fits height (bottom-top) and width max_w."""
    span = bottom - top

    def fits(w, f):
        bb = d.textbbox((0, 0), w, font=f, stroke_width=3)
        return bb[2] - bb[0] <= span and ink_h(d, "H", f) <= max_w

    if not fits(word, face("condensed_black", 48)) and len(word.split()[-1]) >= 4:
        word = word.split()[-1]                    # 'DEMOCRATIC REPUBLIC OF THE CONGO' -> 'CONGO'
    s = 170
    while s > 40 and not fits(word, face("condensed_black", s)):
        s -= 2
    f = face("condensed_black", s)
    while len(word) > 1 and not fits(word, f):     # very long origin: shorten, never overflow
        word = word[:-2].rstrip() + "…"
    lay = text_layer(word, f, pad=0, outline=3).transpose(Image.ROTATE_90)
    paste_ink(im, lay, x, bottom - lay.height)
    return lay.width


def render(data):
    im, d = new_canvas()
    T, B = MARGIN, H - MARGIN
    dose = dose_text(data)
    word = (val(data, "origin") or val(data, "region") or "Coffee").upper()

    col = _vertical_word(im, d, word, MARGIN - 4, T, B, 108)
    X = MARGIN - 4 + col + 14
    d.rectangle([X, T, X + 1, B], fill=BLACK)
    L, R = X + 16, W - MARGIN
    mw = R - L

    # bottom: dose + sealed
    seal = val(data, "seal_date")
    roast = val(data, "roast_date")
    y_b = B
    sf, vf = face("bold", 16), face("bold", 24)
    for k, v in (("ROASTED", roast), ("SEALED", seal)):
        if v:
            d.text((L, y_b), ellipsize(d, v, vf, mw), font=vf, fill=BLACK, anchor="ld")
            y_b -= 28
            d.text((L, y_b), k, font=sf, fill=BLACK, anchor="ld")
            y_b -= 24
    if dose:
        uf = face("condensed", 52)
        gf, _ = fit_line(d, dose, mw - tw(d, "g", uf) - 6, 128, 48, "condensed")
        base = y_b - 4
        d.text((L - 3, base), dose, font=gf, fill=BLACK, anchor="ls")
        d.text((L - 3 + tw(d, dose, gf) + 4, base), "g", font=uf, fill=BLACK, anchor="ls")
        y_b = base - ink_h(d, "0", gf) - 14
    hr(d, y_b, L, R, w=3)
    limit = y_b - 14

    # top: roaster, name, details, notes
    y = T
    roaster = val(data, "roaster").upper()
    if roaster:
        rf, roaster = fit_line(d, roaster, mw, MIN_PX)
        spaced(d, ellipsize_spaced(d, roaster, rf, mw, 2), L, y, rf, spacing=2)
        y += 30
    details = [val(data, "region"), val(data, "producer"), val(data, "process"),
               val(data, "variety"), val(data, "altitude")]
    sparse = not any(details) and not val(data, "notes")
    f, lines, lh = fit_block_face(d, val(data, "coffee_name") or "Coffee", mw,
                                  min(260, limit - y) if sparse else 140, 34, 20,
                                  "bold", leading=1.06, max_lines=7 if sparse else 4)
    y = draw_lines(d, L, y, lines, f, lh) + 10
    for t in [t for t in details if t]:
        f2, ls, lh2 = fit_block_face(d, t, mw, 46, 21, MIN_PX, "regular", leading=1.12, max_lines=2)
        if y + len(ls) * lh2 > limit:
            break
        y = draw_lines(d, L, y, ls, f2, lh2) + 3
    notes = val(data, "notes")
    if notes and limit - y >= 40:
        y += 8
        f3, ls, lh3 = fit_block_face(d, notes, mw, limit - y, 21, MIN_PX, "oblique", leading=1.15)
        draw_lines(d, L, y, ls, f3, lh3)
    return finish(im)
