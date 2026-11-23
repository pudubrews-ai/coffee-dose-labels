"""Side A: a record in thin grooves with the dose on the centre label; tasting notes as the tracklist."""
import math
from .common import *

NAME = "Side A"
ORDER = 12


def _record(im, d, cx, cy, r, label_r, tracks, dose):
    # grooves: thin rings, with a blank gap between "tracks"
    pitch = 7
    radii = list(range(r - 4, label_r + 10, -pitch))
    n = max(1, min(tracks, 5))
    gaps = {radii[int(len(radii) * k / n)] for k in range(1, n)} if n > 1 else set()
    ring(d, cx, cy, r, w=3)
    for rr in radii[1:]:
        if rr not in gaps:
            ring(d, cx, cy, rr, w=2)
    # sheen: wipe two opposite wedges of grooves for a light reflection
    for a0 in (-62, 118):
        d.pieslice([cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6], a0, a0 + 16, fill=WHITE)
    d.ellipse([cx - label_r - 6, cy - label_r - 6, cx + label_r + 6, cy + label_r + 6], fill=WHITE)
    ring(d, cx, cy, label_r, w=3)
    ring(d, cx, cy, label_r - 7, w=2)
    # centre label: dose above the spindle hole, unit below
    ring(d, cx, cy + 12, 6, w=2)
    if dose:
        maxw = 2 * math.sqrt(max(1, (label_r - 12) ** 2 - 46 ** 2))
        gf, txt = fit_line(d, dose, maxw, 64, 28, "condensed")
        d.text((cx, cy - 2), txt, font=gf, fill=BLACK, anchor="ms")
    d.text((cx, cy + 26), "GRAMS", font=face("bold", 16), fill=BLACK, anchor="ma")


def render(data):
    im, d = new_canvas()
    L, R = MARGIN, W - MARGIN
    mw = R - L
    dose = fmt_dose(data)
    tracks = notes_list(data, max_items=4)

    # top strip
    tf = face("bold", 20)
    spaced(d, "SIDE A", L, MARGIN, tf, spacing=4)
    rpm = "VACUUM PRESSING"
    d.text((R, MARGIN), rpm, font=face("bold", 16), fill=BLACK, anchor="ra")

    # record
    r = 132
    cx, cy = W // 2, MARGIN + 34 + r
    _record(im, d, cx, cy, r, 74, len(tracks) or 1, dose)
    y = cy + r + 16

    # footer (dates) geometry
    dates = [(k, v) for k, v in (("PRESSED", val(data, "seal_date")), ("ROASTED", val(data, "roast_date"))) if v]
    foot_top = H - MARGIN - len(dates) * 30 - 10
    hr(d, foot_top, w=3)
    yy = foot_top + 12
    for k, v in dates:
        d.text((L, yy + 6), k, font=font(18), fill=BLACK)
        vf = font(26)
        d.text((R - tw(d, v, vf), yy), v, font=vf, fill=BLACK)
        yy += 30

    # title / artist
    name = val(data, "coffee_name") or "Coffee"
    f, lines, lh = fit_block_face(d, name, mw, 64 if tracks else 96, 30, 20, "bold", leading=1.08,
                                  max_lines=2 if tracks else 3)
    y = draw_lines(d, L, y, lines, f, lh)
    artist = val(data, "roaster")
    if artist:
        af, artist = fit_line(d, artist, mw, 22, 17, "regular")
        d.text((L, y + 2), artist, font=af, fill=BLACK)
        y += 28
    y += 6

    # tracklist
    bottom = foot_top - 8
    if tracks:
        nf, kf = face("regular", 21), face("bold", 18)
        for i, t in enumerate(tracks, 1):
            if y + 26 > bottom - (24 if i == 1 else 0):
                break
            d.text((L, y + 3), f"A{i}", font=kf, fill=BLACK)
            d.text((L + 38, y), ellipsize(d, t, nf, mw - 38), font=nf, fill=BLACK)
            y += 26
        y += 4
    # liner credits: origin, process, variety, altitude
    credits = join(val(data, "origin"), val(data, "process"),
                   val(data, "variety"), val(data, "altitude"))
    if credits and bottom - y >= 20:
        cf, ls, clh = fit_block_face(d, credits, mw, bottom - y, 18, 16, "oblique", leading=1.15, max_lines=2)
        draw_lines(d, L, y, ls, cf, clh)
    return finish(im)
