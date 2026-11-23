"""Big Dose: the dose is the hero."""
from .common import *

NAME = "Big Dose"
ORDER = 2


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw, cx = R - L, W // 2
    dose = dose_text(data)
    y = MARGIN
    # dose (or an em dash placeholder, sized as if it were "18" so the layout doesn't jump)
    unit = font(80)
    uw = tw(d, "g", unit)
    gf = font(fit_size(d, dose_measure(dose), mw - uw - 10, 250, 80))
    gw = dose_w(d, dose, gf)
    x0 = cx - (gw + uw + 10) / 2
    base = y + 6 + ink_h(d, "0", gf)                 # baseline from digit cap height, not the glyph
    draw_dose(d, (x0, base), dose, gf, anchor="ls")
    g_desc = d.textbbox((0, 0), "g", font=unit, anchor="ls")[3]
    d.text((x0 + gw + 10, base - g_desc), "g", font=unit, fill=BLACK, anchor="ls")
    y = base + 24
    d.rectangle([L, y, R, y + 3], fill=BLACK); y += 22

    rows = [(k, v) for k, v in (("SEALED", val(data, "seal_date")), ("ROASTED", val(data, "roast_date"))) if v]
    foot_top = H - MARGIN - len(rows) * 40 - 14 if rows else H - MARGIN
    limit = foot_top - 12

    sparse = not (val(data, "roaster") and val(data, "process"))
    f, lines, lh = fit_block(d, val(data, "coffee_name") or "Coffee", mw, 200 if sparse else 130, 46, 26,
                             leading=1.1, max_lines=5 if sparse else 3)
    y = draw_lines(d, 0, y, lines, f, lh, anchor="c", cx=cx) + 6
    roaster = val(data, "roaster")
    if roaster:
        f2, ls, lh2 = fit_block(d, roaster, mw, 2 * 32, 28, bold=False, leading=1.15, max_lines=2)
        y = draw_lines(d, 0, y, ls, f2, lh2, anchor="c", cx=cx) + 2
    # origin · process: wraps up to 3 lines at >= MIN_PX; lowest-priority parts drop first
    room = max(0, min(3, (limit - y) // int(MIN_PX * 1.2)))
    if room:
        og = fit_parts(d, [(val(data, "origin"), 0), (val(data, "process"), 1)],
                       mw, room, MIN_PX, "regular")
        if og:
            f3, ls, lh3 = fit_block(d, og, mw, min(room * 30, limit - y), 24, bold=False, leading=1.2,
                                    max_lines=room)
            y = draw_lines(d, 0, y, ls, f3, lh3, anchor="c", cx=cx)
    # tasting notes fill the space between the details and the dates, when there is room
    notes = val(data, "notes")
    if notes and limit - y >= 44:
        y += 14
        f4, ls, lh4 = fit_block_face(d, notes, mw, min(3 * 29, limit - y), 24, MIN_PX, "oblique",
                                     leading=1.2, max_lines=3)
        draw_lines(d, 0, y, ls, f4, lh4, anchor="c", cx=cx)

    if rows:
        top = foot_top
        d.rectangle([L, top, R, top + 1], fill=BLACK)
        yy = top + 14
        for k, v in rows:
            d.text((L, yy + 6), k, font=font(20), fill=BLACK)
            vf, v = fit_line(d, v, mw - tw(d, k, font(20)) - 16, 30)
            d.text((R, yy + font(30).getmetrics()[0]), v, font=vf, fill=BLACK, anchor="rs")
            yy += 40
    return finish(im)
