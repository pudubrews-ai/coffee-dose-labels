"""Compact Details: labelled rows, notes, bordered dose/date footer."""
from .common import *

NAME = "Compact Details"
ORDER = 3


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw = R - L
    y = MARGIN
    roaster = val(data, "roaster").upper()
    if roaster:
        f, ls, sp = fit_spaced(d, roaster, mw, 20, spacing=2)
        for ln in ls:
            spaced(d, ln, L, y, f, spacing=sp)
            y += round(f.size) + 5
        y += 30 - round(f.size) - 5
    n_rows = sum(1 for k in ("origin", "region", "producer", "process", "variety", "altitude", "notes")
                 if val(data, k))
    sparse = n_rows <= 2                     # little else to show: a long name may take 5 lines
    f, lines, lh = fit_block(d, val(data, "coffee_name") or "Coffee", mw, 160 if sparse else 90, 38, 24,
                             leading=1.08, max_lines=5 if sparse else 2)
    y = draw_lines(d, L, y, lines, f, lh) + 6
    hr(d, y, w=3); y += 10

    # footer box
    dose = dose_text(data)
    dates = [(k, v) for k, v in (("SEALED", val(data, "seal_date")), ("ROASTED", val(data, "roast_date"))) if v]
    box_h = (66 if dose else 0) + len(dates) * 30 + 20
    box_top = H - MARGIN - box_h
    LW = 112                                   # label column width
    rows = [("ORIGIN", val(data, "origin")), ("REGION", val(data, "region")),
            ("FARM", val(data, "producer")), ("PROCESS", val(data, "process")),
            ("VARIETY", val(data, "variety")), ("ALTITUDE", val(data, "altitude"))]
    rows = [(k, v) for k, v in rows if v]
    notes = val(data, "notes")
    vf = font(24)
    for k, v in rows:
        ls = wrap(d, v, vf, mw - LW, max_lines=2)
        if y + len(ls) * 28 > box_top - 12: break
        d.text((L, y + 5), k, font=font(16), fill=BLACK)
        draw_lines(d, L + LW, y, ls, vf, 28)
        y += len(ls) * 28 + 6
    if notes and box_top - 12 - (y + 26) >= 22:      # caption only when a line of notes fits under it
        y += 4
        d.text((L, y), "NOTES", font=font(16), fill=BLACK); y += 22
        avail = box_top - 12 - y
        if avail >= 22:
            f3, ls, lh3 = fit_block(d, notes, mw, avail, 24, MIN_PX, bold=False, leading=1.18)
            draw_lines(d, L, y, ls, f3, lh3)

    d.rectangle([L, box_top, R, H - MARGIN], outline=BLACK, width=3)
    y = box_top + 12
    if dose:
        gf = font(56)
        draw_dose(d, (L + 12, y - 4), dose, gf)
        d.text((L + 12 + dose_w(d, dose, gf) + 6, y + 22), "g", font=font(30), fill=BLACK)
        y += 64
    for k, v in dates:
        d.text((L + 12, y + 5), k, font=font(16), fill=BLACK)
        vf2, v = fit_line(d, v, mw - 24 - tw(d, k, font(16)) - 14, 24)
        d.text((R - 12, y + font(24).getmetrics()[0]), v, font=vf2, fill=BLACK, anchor="rs")
        y += 30
    return finish(im)
