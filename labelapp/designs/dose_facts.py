"""Dose Facts: a nutrition-panel parody. Serving size = the dose, coffee details as panel rows."""
from .common import *

NAME = "Dose Facts"
ORDER = 14


def _row(d, L, R, y, label, value, indent=0, rule=True, size=21):
    """'Label value' row with a hairline above; value ellipsized to fit. Returns next y."""
    if rule:
        d.rectangle([L + indent, y, R, y + 1], fill=BLACK)
    y += 5
    lf, vf = face("bold", size), face("regular", size)
    x = L + indent
    d.text((x, y), label, font=lf, fill=BLACK)
    x += tw(d, label, lf) + 8
    vf, value = fit_short(d, value, R - x, size, size, "regular")
    d.text((x, y), value, font=vf, fill=BLACK)
    return y + size + 4


def render(data):
    im, d = new_canvas()
    BL, BR, BT, BB = MARGIN - 10, W - MARGIN + 10, MARGIN - 10, H - MARGIN + 10
    d.rectangle([BL, BT, BR, BB], outline=BLACK, width=2)
    L, R = BL + 12, BR - 12
    mw = R - L
    dose = dose_text(data)
    y = BT + 6

    # title + product
    tf, title = fit_line(d, "Dose Facts", mw + 4, 70, 40, "condensed_black")
    d.text((L - 2, y + ink_h(d, "D", tf) + 2), title, font=tf, fill=BLACK, anchor="ls")
    y += ink_h(d, "D", tf) + 10
    d.rectangle([L, y, R, y + 1], fill=BLACK); y += 6
    n_rows = sum(1 for k in ("origin", "region", "producer", "process", "variety", "altitude", "notes")
                 if val(data, k))
    sparse = n_rows <= 2                     # few panel rows: a long name may take 4 lines
    f, lines, lh = fit_block_face(d, val(data, "coffee_name") or "Coffee", mw, 96 if sparse else 50, 23,
                                  MIN_PX, "bold", leading=1.08, max_lines=4 if sparse else 2)
    y = draw_lines(d, L, y, lines, f, lh)
    roaster = val(data, "roaster")
    if roaster:
        rf, roaster = fit_line(d, roaster, mw, 20, style="regular")
        d.text((L, y), roaster, font=rf, fill=BLACK)
        y += 24
    y += 4
    d.rectangle([L, y, R, y + 4], fill=BLACK); y += 9

    # serving size + dates
    sf = face("bold", 22)
    for k, v in (("Serving size", f"1 dose ({dose}g)" if dose else "1 dose"),
                 ("Sealed", val(data, "seal_date")), ("Roasted", val(data, "roast_date"))):
        if not v:
            continue
        d.text((L, y), k, font=sf, fill=BLACK)
        vf, vv = fit_line(d, v, mw - tw(d, k, sf) - 12, 22)
        d.text((R, y), vv, font=vf, fill=BLACK, anchor="ra")
        y += 27
    y += 2
    d.rectangle([L, y, R, y + 9], fill=BLACK); y += 13

    # amount per serving: grams, big
    d.text((L, y), "Amount per serving", font=face("bold", 16), fill=BLACK)
    gf = face("condensed_black", 76)
    if dose:
        gf, _ = fit_line(d, dose, mw - 130, 76, 40, "condensed_black")
    base = y + 20 + ink_h(d, "0", gf)
    d.text((L, base), "Grams", font=face("condensed_black", 44), fill=BLACK, anchor="ls")
    if dose:
        d.text((R, base), dose, font=gf, fill=BLACK, anchor="rs")
    y = base + 8
    d.rectangle([L, y, R, y + 4], fill=BLACK); y += 8

    # bottom block, laid out bottom-up: footnote, notes, joy row
    ff = face("regular", 16)
    foot_y = BB - 8 - 18
    d.text((L, foot_y), "* Based on one good cup a day.", font=ff, fill=BLACK)
    d.rectangle([L, foot_y - 7, R, foot_y - 6], fill=BLACK)
    bottom = foot_y - 7
    notes = val(data, "notes")
    if notes:
        nf, nl, nlh = fit_block_face(d, "Tasting notes: " + notes, mw, 3 * 22, 19, MIN_PX,
                                     "regular", leading=1.15, max_lines=3)
        top = bottom - 6 - len(nl) * nlh
        draw_lines(d, L, top, nl, nf, nlh)
        bottom = top - 6
        d.rectangle([L, bottom - 9, R, bottom], fill=BLACK)
        bottom -= 9
    # % Daily Joy column header + detail rows; when short of room, drop the least useful first
    d.text((R, y), "% Daily Joy*", font=face("bold", 16), fill=BLACK, anchor="ra")
    y += 22
    rows = [("Origin", val(data, "origin"), 0), ("Region", val(data, "region"), 22),
            ("Producer", val(data, "producer"), 0), ("Process", val(data, "process"), 0),
            ("Variety", val(data, "variety"), 0), ("Altitude", val(data, "altitude"), 0)]
    rows = [r for r in rows if r[1]]
    pitch = 30
    fit = max(0, (bottom - 32 - y) // pitch)      # rows are 21 px; drop rows rather than shrink
    for k in ("Producer", "Region", "Altitude", "Variety", "Process", "Origin"):
        if len(rows) <= fit:
            break
        rows = [r for r in rows if r[0] != k]
    for k, v, ind in rows:
        y = _row(d, L, R, y, k, v, indent=ind, size=21)
    d.rectangle([L, y, R, y + 1], fill=BLACK)
    jf = face("bold", 22)
    d.text((L, y + 5), "Joy", font=jf, fill=BLACK)
    d.text((R, y + 5), "100%", font=jf, fill=BLACK, anchor="ra")
    return finish(im)
