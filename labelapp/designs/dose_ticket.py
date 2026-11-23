"""Dose Ticket: boarding pass from origin to VAC, dose as the seat, tear-off stub."""
from .common import *

NAME = "Dose Ticket"
ORDER = 10


def _label(d, x, y, text):
    d.text((x, y), text, font=face("bold", 16), fill=BLACK)


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw = R - L
    dose = fmt_dose(data)
    seal = val(data, "seal_date")
    code = origin_code(data)
    batch = batch_code(data)

    # header: outlined band, carrier + pass type
    d.rectangle([L, MARGIN, R, MARGIN + 40], outline=BLACK, width=3)
    tf = face("bold", 16)
    d.text((R - 12, MARGIN + 21), "BOARDING PASS", font=tf, fill=BLACK, anchor="rm")
    roaster = val(data, "roaster").upper() or "SINGLE DOSE"
    hf, roaster = fit_line(d, roaster, mw - 24 - tw(d, "BOARDING PASS", tf) - 16, 20, 14)
    d.text((L + 12, MARGIN + 21), roaster, font=hf, fill=BLACK, anchor="lm")
    y = MARGIN + 40 + 18

    # route: ETH ----> VAC
    rf = face("condensed", 76)
    base = y + ink_h(d, "VAC", rf)
    d.text((L, base), code, font=rf, fill=BLACK, anchor="ls")
    d.text((R, base), "VAC", font=rf, fill=BLACK, anchor="rs")
    a0, a1 = L + tw(d, code, rf) + 14, R - tw(d, "VAC", rf) - 14
    am = base - ink_h(d, "VAC", rf) // 2
    dashed_h(d, am - 1, a0, a1 - 12, dash=6, gap=5, w=3)
    d.polygon([(a1, am), (a1 - 14, am - 9), (a1 - 14, am + 9)], fill=BLACK)
    y = base + 8
    sf = face("regular", 18)
    origin = val(data, "origin") or val(data, "region") or "Coffee beans"
    d.text((L, y), ellipsize(d, origin, sf, mw / 2 - 10), font=sf, fill=BLACK)
    d.text((R, y), "Vacuum sealed", font=sf, fill=BLACK, anchor="ra")
    y += 30

    # passenger / details
    hr(d, y, w=2); y += 10
    _label(d, L, y, "PASSENGER"); y += 22
    f, lines, lh = fit_block_face(d, val(data, "coffee_name") or "Coffee", mw, 96, 34, 22,
                                  "bold", leading=1.1, max_lines=3)
    y = draw_lines(d, L, y, lines, f, lh) + 4

    # stub geometry (fixed at the bottom)
    stub_top = H - MARGIN - 100
    grid_bottom = stub_top - 22

    # SEAT (dose) box + CLASS / GATE column
    box_h = 112
    box_top = grid_bottom - box_h
    seat_w = 200
    d.rectangle([L, box_top, L + seat_w, grid_bottom], outline=BLACK, width=3)
    _label(d, L + 12, box_top + 10, "SEAT")
    if dose:
        gf = face("condensed", 80)
        uf = face("bold", 36)
        gw, uw = tw(d, dose, gf), tw(d, "g", uf)
        if gw + uw + 6 > seat_w - 24:
            gf, _ = fit_line(d, dose, seat_w - 30 - uw, 88, 40, "condensed")
            gw = tw(d, dose, gf)
        bx = L + 12
        bb = grid_bottom - 16
        d.text((bx, bb), dose, font=gf, fill=BLACK, anchor="ls")
        d.text((bx + gw + 6, bb), "g", font=uf, fill=BLACK, anchor="ls")

    cells = [(k, v) for k, v in (("CLASS", val(data, "process")), ("TYPE", val(data, "variety")),
                                 ("ALTITUDE", val(data, "altitude"))) if v][:2]
    cx0 = L + seat_w + 14
    cw = R - cx0
    cy = box_top
    ch = box_h // 2
    vs = min([fit_line(d, v, cw, 26, 18, "condensed")[0].size for _, v in cells] or [26])
    for k, v in cells:
        _label(d, cx0, cy + 6, k)
        vf = face("condensed", vs)
        d.text((cx0, cy + ch - 9), ellipsize(d, v, vf, cw), font=vf, fill=BLACK, anchor="ls")
        cy += ch
    if len(cells) == 2:
        dashed_h(d, box_top + ch, cx0, R, dash=4, gap=4, w=2)

    # in-flight menu (notes) / carrier region fill the gap above the grid
    avail = box_top - 14 - y
    notes = val(data, "notes")
    if notes and avail >= 44:
        y += 4
        _label(d, L, y, "IN-FLIGHT MENU"); y += 22
        f3, ls, lh3 = fit_block_face(d, notes, mw, box_top - 14 - y, 22, 17, "regular", leading=1.2)
        y = draw_lines(d, L, y, ls, f3, lh3)

    # perforation with punched notches
    py = stub_top - 10
    dashed_h(d, py, L + 14, R - 14, dash=6, gap=6, w=2)
    for x in (0, W):
        d.ellipse([x - 12, py - 11, x + 12, py + 12], outline=BLACK, width=2)

    # stub: sealed date, dose repeat, decorative bars
    y = stub_top + 4
    _label(d, L, y, "SEALED")
    _label(d, R - 64, y, "SEAT")
    vf = face("bold", 30)
    if seal:
        sv = ellipsize(d, seal.upper(), vf, mw - 90)
        d.text((L, y + 22), sv, font=vf, fill=BLACK)
    if dose:
        df, dd = fit_line(d, dose + "g", 64, 30, 18)
        d.text((R, y + 22), dd, font=df, fill=BLACK, anchor="ra")
    fake_barcode(d, L, y + 62, R - 96, H - MARGIN - 2, seed=batch + dose)
    mf = face("mono_bold", 18)
    d.text((R, H - MARGIN), f"VS{batch}", font=mf, fill=BLACK, anchor="rd")
    return finish(im)
