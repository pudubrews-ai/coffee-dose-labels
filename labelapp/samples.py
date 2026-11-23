"""Generate docs/samples/*.png. Run: python -m labelapp.samples"""
import os
from . import designs
from .designs.common import fmt_date
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

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "samples")
    os.makedirs(out, exist_ok=True)
    for k in designs.registry():
        for n, dd in (("full", FULL), ("sparse_long", SPARSE), ("mid", MID)):
            im = designs.render(k, dd)
            assert im.mode == "1" and im.size == (400, 640)
            im.save(os.path.join(out, f"{k}_{n}.png"))
    print("ok")
