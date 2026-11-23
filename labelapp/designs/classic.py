"""Classic: roaster, big coffee name, details, bottom dose/dates block."""
from .common import *

NAME = "Classic"
ORDER = 1


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw = R - L
    y = MARGIN

    roaster = val(data, "roaster").upper()
    if roaster:
        s = fit_size(d, roaster, mw, 22)
        f = font(s)
        spaced(d, ellipsize_spaced(d, roaster, f, mw, 3), L, y, f, spacing=3)
        y += s + 12

    # bottom block geometry (dose + dates)
    dose = dose_text(data)
    seal, roast = val(data, "seal_date"), val(data, "roast_date")
    dates = [("SEALED", seal), ("ROASTED", roast)]
    dates = [(k, v) for k, v in dates if v]
    foot_h = 40 + (len(dates) * 30 if dates else 0) + (110 if dose else 0)
    foot_top = H - MARGIN - foot_h

    name = val(data, "coffee_name") or "Coffee"
    n_body = sum(1 for k in ("producer", "process", "variety", "altitude", "notes") if val(data, k))
    sparse = n_body <= 1                     # little else to show: a long name may take 6 lines
    f, lines, lh = fit_block(d, name, mw, 230 if sparse else 125, 56, 30, leading=1.08,
                             max_lines=6 if sparse else 3)
    y = draw_lines(d, L, y, lines, f, lh)
    y += 8
    hr(d, y, w=3); y += 14

    body = []
    og = join(val(data, "origin"), val(data, "region"))
    if og: body.append((og, True, 28))
    if val(data, "producer"): body.append((val(data, "producer"), False, 24))
    if val(data, "process"): body.append((val(data, "process"), False, 24))
    va = join(val(data, "variety"), val(data, "altitude"))
    if va: body.append((va, False, 24))
    for text, bold, size in body:
        f2, ls, lh2 = fit_block(d, text, mw, 2 * int(size * 1.2), size, MIN_PX, bold=bold, leading=1.15,
                                max_lines=2)
        if y + len(ls) * lh2 > foot_top - 10: break
        y = draw_lines(d, L, y, ls, f2, lh2) + 4
    notes = val(data, "notes")
    if notes:
        y += 6
        avail = foot_top - 14 - y
        if avail >= 24:
            f3, ls, lh3 = fit_block(d, notes, mw, avail, 26, MIN_PX, bold=False, leading=1.2)
            draw_lines(d, L, y, ls, f3, lh3)

    # footer
    hr(d, foot_top, w=3)
    y = foot_top + 14
    if dose:
        gf = font(104)
        unit = font(48)
        gw, uw = tw(d, dose, gf), tw(d, "g", unit)
        if gw + uw + 8 > mw:
            gf = font(fit_size(d, dose, mw - uw - 8, 104, 40)); gw = tw(d, dose, gf)
        d.text((L, y - 6), dose, font=gf, fill=BLACK)
        d.text((L + gw + 8, y + 48), "g", font=unit, fill=BLACK)
        y += 110
    for k, v in dates:
        d.text((L, y + 6), k, font=font(20), fill=BLACK)
        vf = font(28)
        d.text((R - tw(d, v, vf), y), v, font=vf, fill=BLACK)
        y += 30
    return finish(im)
