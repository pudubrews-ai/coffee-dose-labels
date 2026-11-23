"""Big Dose: the dose is the hero."""
from .common import *

NAME = "Big Dose"
ORDER = 2


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw, cx = R - L, W // 2
    dose = fmt_dose(data)
    y = MARGIN
    if dose:
        unit = font(80)
        uw = tw(d, "g", unit)
        s = fit_size(d, dose, mw - uw - 10, 250, 80)
        gf = font(s)
        gw = tw(d, dose, gf)
        x0 = cx - (gw + uw + 10) / 2
        top = d.textbbox((0, 0), dose, font=gf)[1]
        d.text((x0, y - top + 6), dose, font=gf, fill=BLACK)
        bb = d.textbbox((0, 0), "g", font=unit)
        base = y - top + 6 + d.textbbox((0, 0), dose, font=gf)[3]
        d.text((x0 + gw + 10, base - bb[3]), "g", font=unit, fill=BLACK)
        y = base + 24
    d.rectangle([L, y, R, y + 3], fill=BLACK); y += 22

    f, lines, lh = fit_block(d, val(data, "coffee_name") or "Coffee", mw, 130, 46, 26, leading=1.1, max_lines=3)
    y = draw_lines(d, 0, y, lines, f, lh, anchor="c", cx=cx) + 6
    roaster = val(data, "roaster")
    if roaster:
        f2 = font(fit_size(d, roaster, mw, 28, 16, bold=False), False)
        y = draw_lines(d, 0, y, [ellipsize(d, roaster, f2, mw)], f2, 34, anchor="c", cx=cx)
    og = join(val(data, "origin"), val(data, "process"))
    if og:
        f3 = font(fit_size(d, og, mw, 24, 16, bold=False), False)
        y = draw_lines(d, 0, y + 2, [ellipsize(d, og, f3, mw)], f3, 30, anchor="c", cx=cx)

    rows = [(k, v) for k, v in (("SEALED", val(data, "seal_date")), ("ROASTED", val(data, "roast_date"))) if v]
    if rows:
        top = H - MARGIN - len(rows) * 40 - 14
        d.rectangle([L, top, R, top + 1], fill=BLACK)
        yy = top + 14
        for k, v in rows:
            d.text((L, yy + 6), k, font=font(20), fill=BLACK)
            vf = font(30)
            d.text((R - tw(d, v, vf), yy), v, font=vf, fill=BLACK)
            yy += 40
    return finish(im)
