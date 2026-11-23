"""Generate docs/samples/*.png and the contact sheets. Run: python -m labelapp.samples"""
import os
from PIL import Image, ImageDraw
from . import designs
from .designs.common import fmt_date, face
from datetime import date

FULL = dict(roaster="Onyx Coffee Lab", coffee_name="Ethiopia Guji Hambela Natural", origin="Ethiopia",
            region="Guji, Hambela", producer="Kercha Washing Station", process="Natural",
            variety="Heirloom 74110", altitude="2,100 m", notes="Blueberry jam, dark chocolate, jasmine",
            roast_date="Nov 14, 2026", dose="18", seal_date=fmt_date(date(2026, 11, 23)))
SPARSE = dict(roaster="", coffee_name="Super Extra Ultra Long Named Single Origin Reserve Lot 47 Anaerobic Honey Experimental Microlot Edition",
              origin="Colombia", dose="22.5", seal_date="Nov 23, 2026")
MID = dict(roaster="Tim Wendelboe", coffee_name="Kenya Kiambu Karindundu AA", origin="Kenya", region="Kiambu",
           process="Washed", variety="SL28, SL34", notes="Blackcurrant, grapefruit, brown sugar, with a very long tail of extra descriptors to test fit",
           dose="15", seal_date="Nov 23, 2026")

# Stress set: very long process and name, no roast date, no dose yet (preview state).
SEYLONG = dict(roaster="SEY", coffee_name="Pepe Jijon Finca Soledad Mejorado - TyOxy", origin="Ecuador",
               region="Imbabura", producer="Pepe Jijon, Finca Soledad",
               process="Washed (TyOxy: oxidation, 48h dry fermentation, then washed)", variety="Mejorado",
               altitude="1,515 masl", notes="hibiscus, raspberry, tree tomato, fig", roast_date=None, dose="",
               seal_date="Nov 23, 2026")
# Real coffees as extracted by labelapp.extract (Nov 2026) from 8 roaster pages and a
# synthetic test bag photo ('photo': Northwind is not a real roaster), dose filled.
REAL = [
    ('sey', {'roaster': 'SEY',
             'coffee_name': 'Finca Soledad',
             'origin': 'Ecuador',
             'region': 'Imbabura',
             'producer': 'Pepe Jijon',
             'process': 'Washed TyOxy',
             'variety': 'Mejorado',
             'altitude': '1,515 masl',
             'notes': 'Hibiscus, raspberry, tree tomato, fig',
             'dose': '18',
             'seal_date': 'Nov 23, 2026'}),
    ('onyx', {'roaster': 'Onyx Coffee Lab',
              'coffee_name': 'Jhoan Vergara',
              'origin': 'Colombia',
              'region': 'Huila',
              'producer': 'Las Flores',
              'process': 'Washed',
              'variety': 'Gesha',
              'altitude': '1,750 meters',
              'dose': '17.5',
              'seal_date': 'Nov 23, 2026'}),
    ('ccc', {'roaster': 'Counter Culture Coffee',
             'coffee_name': 'Finca Idania',
             'origin': 'El Salvador',
             'region': 'Chalatenango',
             'producer': 'Finca Idania (Héctor Saul Reina)',
             'process': 'Washed',
             'variety': 'Pacamara',
             'altitude': '1,600–1,700 meters',
             'notes': 'red grape, chocolate, plum',
             'dose': '20',
             'seal_date': 'Nov 23, 2026'}),
    ('dak', {'roaster': 'Dak Coffee Roasters',
             'coffee_name': 'Peachy Daze',
             'origin': 'Ethiopia',
             'region': 'Gedeb',
             'producer': 'Chelbesa Washing Station',
             'process': 'Washed',
             'variety': 'Heirloom',
             'altitude': '2173 masl',
             'notes': 'Elderflower, Lemon, White Peach, Black Tea',
             'dose': '18',
             'seal_date': 'Nov 23, 2026'}),
    ('lacabra', {'roaster': 'La Cabra',
                 'coffee_name': 'Concepción',
                 'origin': 'Guatemala',
                 'region': 'Jalapa',
                 'producer': 'Vanessa Braun Valle',
                 'process': 'Washed',
                 'variety': 'Pacamara',
                 'altitude': '1770 masl',
                 'notes': 'floral, stone fruit, melon, spiced finish',
                 'dose': '16.5',
                 'seal_date': 'Nov 23, 2026'}),
    ('wendelboe', {'roaster': 'Tim Wendelboe Coffee',
                   'coffee_name': 'Los Pirineos',
                   'origin': 'El Salvador',
                   'region': 'Tecapa-Chinameca, Usulutan',
                   'producer': 'Diego Baraona',
                   'process': 'Honey',
                   'variety': 'Pacamara',
                   'altitude': '1100 – 1400 masl',
                   'notes': 'Winey, stone fruits, cacao nibs',
                   'dose': '15',
                   'seal_date': 'Nov 23, 2026'}),
    ('populus', {'roaster': 'Populus Coffee',
                 'coffee_name': 'Eudis Orosco',
                 'origin': 'Peru',
                 'region': 'Incahuasi, Cusco',
                 'producer': 'Eudis Orosco',
                 'process': 'Washed',
                 'variety': 'SL9 (Geisha Inca)',
                 'altitude': '2230 masl',
                 'notes': 'aromatic citruses, lemon verbena, white florals, jasmine, lingering sweetness',
                 'dose': '18',
                 'seal_date': 'Nov 23, 2026'}),
    ('populus2', {'roaster': 'Populus Coffee',
                  'coffee_name': 'Kamunyaka',
                  'origin': 'Kenya',
                  'region': 'Nyeri',
                  'producer': 'Kamunyaka Coffee Factory, Iria-ini Farmers Cooperative Society',
                  'process': 'Natural',
                  'variety': 'SL28, SL34',
                  'altitude': '1750-1800 masl',
                  'notes': 'dark grapes, sweet citrus, raspberries, black tea, lemonade-like acidity',
                  'dose': '22',
                  'seal_date': 'Nov 23, 2026'}),
    ('photo', {'roaster': 'Northwind Coffee Roasters',
               'coffee_name': 'Worka Chelbesa',
               'origin': 'Ethiopia',
               'region': 'Gedeb, Gedeo',
               'process': 'Washed',
               'variety': 'Heirloom 74158',
               'altitude': '2,050–2,200 masl',
               'notes': 'Peach, bergamot, black tea',
               'roast_date': 'Nov 12, 2026',
               'dose': '9',
               'seal_date': 'Nov 23, 2026'}),
]
SETS = (("full", FULL), ("sparse_long", SPARSE), ("mid", MID), ("seylong", SEYLONG))


def grid(out, name, tiles):
    """3-column grid of (caption, 1-bit image) tiles on grey."""
    pad, cap = 24, 24
    cols, rows = 3, (len(tiles) + 2) // 3
    sheet = Image.new("L", (cols * 400 + (cols + 1) * pad, rows * (640 + cap) + (rows + 1) * pad), 200)
    d = ImageDraw.Draw(sheet)
    for i, (caption, im) in enumerate(tiles):
        x = pad + (i % cols) * (400 + pad)
        y = pad + (i // cols) * (640 + cap + pad)
        sheet.paste(im.convert("L"), (x, y))
        d.text((x, y + 640 + 4), caption, font=face("regular", 15), fill=0)
    sheet.save(os.path.join(out, name))


def contact_sheet(out, suffix, name):
    """3x3 grid of <design>_<suffix>.png, design id under each."""
    grid(out, name, [(k, Image.open(os.path.join(out, f"{k}_{suffix}.png")))
                     for k in designs.registry()])


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
    # one real extracted coffee per design (every design has been checked with every real coffee)
    grid(out, "contact_sheet_real.png", [(f"{k} · {name}", designs.render(k, dd))
                                         for k, (name, dd) in zip(designs.registry(), REAL)])
    print("ok")
