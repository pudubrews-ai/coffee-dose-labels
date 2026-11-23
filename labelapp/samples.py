"""Generate docs/samples/*.png and the contact sheets. Run: python -m labelapp.samples"""
import os
from PIL import Image, ImageDraw
from . import designs
from .designs.common import fmt_date, face
from datetime import date

FULL = dict(roaster="Onyx Coffee Lab", coffee_name="Ethiopia Guji Hambela Natural", origin="Ethiopia",
            region="Guji, Hambela", producer="Kercha Washing Station", process="Natural",
            variety="Heirloom 74110", altitude="2,100 m", notes="Blueberry jam, dark chocolate, jasmine",
            roast_date="14 Nov 2026", dose="18", seal_date=fmt_date(date(2026, 11, 23)))
SPARSE = dict(roaster="", coffee_name="Super Extra Ultra Long Named Single Origin Reserve Lot 47 Anaerobic Honey Experimental Microlot Edition",
              origin="Colombia", dose="22.5", seal_date="23 Nov 2026")
MID = dict(roaster="Tim Wendelboe", coffee_name="Kenya Kiambu Karindundu AA", origin="Kenya", region="Kiambu",
           process="Washed", variety="SL28, SL34", notes="Blackcurrant, grapefruit, brown sugar, with a very long tail of extra descriptors to test fit",
           dose="15", seal_date="23 Nov 2026")

# Stress set: very long process and name, no roast date, no dose yet (preview state).
SEYLONG = dict(roaster="SEY", coffee_name="Pepe Jijon Finca Soledad Mejorado - TyOxy", origin="Ecuador",
               region="Imbabura", producer="Pepe Jijon, Finca Soledad",
               process="Washed (TyOxy: oxidation, 48h dry fermentation, then washed)", variety="Mejorado",
               altitude="1,515 masl", notes="hibiscus, raspberry, tree tomato, fig", roast_date=None, dose="",
               seal_date="23 Nov 2026")
SETS = (("full", FULL), ("sparse_long", SPARSE), ("mid", MID), ("seylong", SEYLONG))


def contact_sheet(out, suffix, name):
    """3x3 grid of <design>_<suffix>.png on grey, design id under each."""
    pad, cap = 24, 24
    keys = list(designs.registry())
    cols, rows = 3, (len(keys) + 2) // 3
    sheet = Image.new("L", (cols * 400 + (cols + 1) * pad, rows * (640 + cap) + (rows + 1) * pad), 200)
    d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        x = pad + (i % cols) * (400 + pad)
        y = pad + (i // cols) * (640 + cap + pad)
        sheet.paste(Image.open(os.path.join(out, f"{k}_{suffix}.png")).convert("L"), (x, y))
        d.text((x, y + 640 + 4), k, font=face("regular", 15), fill=0)
    sheet.save(os.path.join(out, name))


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "samples")
    os.makedirs(out, exist_ok=True)
    for k in designs.registry():
        for n, dd in SETS:
            im = designs.render(k, dd)
            assert im.mode == "1" and im.size == (400, 640)
            im.save(os.path.join(out, f"{k}_{n}.png"))
    contact_sheet(out, "full", "contact_sheet.png")
    contact_sheet(out, "seylong", "contact_sheet_seylong.png")
    print("ok")
