"""Specimen: a punched lab sample tag; typed form fields, storage tick-box, dose/date grid."""
from .common import *

NAME = "Specimen"
ORDER = 13

CH = 30                      # chamfer of the tag's top corners


def _tag(d, L, T, R, B):
    pts = [(L, T + CH), (L + CH, T), (R - CH, T), (R, T + CH), (R, B), (L, B), (L, T + CH)]
    d.line(pts, fill=BLACK, width=3, joint="curve")
    cx = (L + R) // 2
    ring(d, cx, T + 26, 11, w=2)          # punched hole
    ring(d, cx, T + 26, 19, w=2)          # reinforcement ring


def _box(d, x, y, ticked, s=18):
    d.rectangle([x, y, x + s, y + s], outline=BLACK, width=2)
    if ticked:
        d.line([(x + 4, y + 4), (x + s - 4, y + s - 4)], fill=BLACK, width=3)
        d.line([(x + s - 4, y + 4), (x + 4, y + s - 4)], fill=BLACK, width=3)


def render(data):
    im, d = new_canvas()
    T, B = MARGIN - 8, H - MARGIN + 8
    TL, TR = MARGIN - 8, W - MARGIN + 8
    _tag(d, TL, T, TR, B)
    L, R = MARGIN + 6, W - MARGIN - 6
    mw = R - L
    dose = fmt_dose(data)

    # heading row under the punch
    y = T + 56
    hf = face("bold", 26)
    spaced(d, "SPECIMEN", L, y, hf, spacing=4)
    mf = face("mono_bold", 20)
    d.text((R, y + 24), f"No.{batch_code(data)}", font=mf, fill=BLACK, anchor="rs")
    y += 36
    hr(d, y, L, R, w=3); y += 12

    # bottom grid geometry
    grid_h = 132
    grid_top = B - 10 - grid_h
    store_y = grid_top - 30

    # form rows
    LW = 96
    lf = face("mono_bold", 16)
    rows = [("SAMPLE", val(data, "coffee_name") or "Coffee", 3, 24),
            ("SOURCE", val(data, "roaster"), 1, 22),
            ("LOCALE", join(val(data, "origin"), val(data, "region"), sep=", "), 2, 22),
            ("FARM", val(data, "producer"), 1, 22),
            ("PREP.", val(data, "process"), 1, 22),
            ("VAR.", val(data, "variety"), 1, 22),
            ("ELEV.", val(data, "altitude"), 1, 22),
            ("OBS.", val(data, "notes"), 3, 20)]
    rows = [r for r in rows if r[1]]
    if len(rows) <= 3:                       # sparse: let a long name take more lines
        rows[0] = ("SAMPLE", rows[0][1], 4, 26)
    limit = store_y - 12
    for i, (k, v, nlines, size) in enumerate(rows):
        room = limit - y - 6
        if room < 24:
            break
        bold = k != "OBS."
        f, ls, lh = fit_block_face(d, v, mw - LW, min(room, int(size * 1.12) * nlines), size,
                                   17, "bold" if bold else "regular", leading=1.12, max_lines=nlines)
        d.text((L, y + 4), k, font=lf, fill=BLACK)
        yy = draw_lines(d, L + LW, y, ls, f, lh)
        y = yy + 2
        dashed_h(d, y, L + LW, R, dash=2, gap=3, w=2)
        y += 7

    # storage tick-boxes
    sf = face("mono_bold", 16)
    x = L
    d.text((x, store_y + 9), "STORAGE", font=sf, fill=BLACK, anchor="lm"); x = L + LW
    for lab, on in (("VACUUM", True), ("AMBIENT", False)):
        _box(d, x, store_y, on)
        d.text((x + 26, store_y + 9), lab, font=face("bold", 18), fill=BLACK, anchor="lm")
        x += 26 + tw(d, lab, face("bold", 18)) + 22

    # dose / dates grid
    gx = L + 174
    d.rectangle([L, grid_top, R, grid_top + grid_h], outline=BLACK, width=3)
    d.rectangle([gx, grid_top, gx + 2, grid_top + grid_h], fill=BLACK)
    d.text((L + 10, grid_top + 8), "DOSE", font=lf, fill=BLACK)
    if dose:
        uf = face("bold", 34)
        gf, txt = fit_line(d, dose, gx - L - 20 - tw(d, "g", uf) - 4, 84, 40, "condensed")
        base = grid_top + grid_h - 16
        d.text((L + 10, base), txt, font=gf, fill=BLACK, anchor="ls")
        d.text((L + 10 + tw(d, txt, gf) + 4, base), "g", font=uf, fill=BLACK, anchor="ls")
    cells = [("SEALED", val(data, "seal_date")), ("ROASTED", val(data, "roast_date"))]
    cells = [c for c in cells if c[1]]
    ch = grid_h // max(1, len(cells))
    for i, (k, v) in enumerate(cells):
        cy = grid_top + i * ch
        if i:
            d.rectangle([gx, cy, R, cy + 1], fill=BLACK)
        d.text((gx + 10, cy + 8), k, font=lf, fill=BLACK)
        vf, v = fit_line(d, v, R - gx - 20, 26, 17, "bold")
        d.text((gx + 10, cy + ch - 14), v, font=vf, fill=BLACK, anchor="ls")
    return finish(im)
