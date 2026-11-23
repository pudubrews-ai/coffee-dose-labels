# Bean dose labels

Local web app that prints 50x80 mm labels for vacuum-sealed coffee doses on a Phomemo M221 over BLE.

## Run
```
./run.sh        # creates .venv, installs deps, serves http://127.0.0.1:8221 and opens the browser
```
Launch it from a terminal that has Bluetooth permission (e.g. Warp). Needs the `claude` CLI logged in (used for extraction; no API keys).

## How it works
1. Paste a roaster URL (page is fetched by the backend, reduced to text/meta/JSON-LD, then passed to `claude -p`) or drop/take a photo of the bag (`claude -p` with only the `Read` tool on a downscaled copy). Page and image text are treated as untrusted data. Results fill editable fields; manual entry always works.
2. Enter dose and copies, pick a design; the preview is the real 1-bit 400x640 PNG rendered server-side.
3. Print sends N copies over one BLE connection, checking paper before each one.

Layout: `labelapp/printer.py` (BLE, CLI: `python -m labelapp.printer status`), `extract.py` (claude CLI), `designs/` (labels), `server.py` (FastAPI), `static/` (UI), `config.py` (printer name, port, model). Samples: `python -m labelapp.samples` writes `docs/samples/`. `prototype/` holds the original probe scripts.

## Printer facts
BLE name = serial `YOUR-PRINTER-BLE-NAME` (change in `config.py`); service ff00, write ff02 (no response), notify ff03. Head 576 px / 203 dpi; label 400x640 px centred (88 px blank each side). Job: `1b40; 1b37 07 78 02; 1d7c 05; 1d7630 00 48 00 80 02 + raster; 1b4a 20`. Status: `1f1108` battery, `1f1111` paper (89 = present), `1f1113` head temp.

## Adding a design
Drop a file in `labelapp/designs/` (e.g. `mine.py`); it appears in the picker automatically.
```python
from .common import *        # font, fit_block, wrap, ellipsize, draw_lines, val, join, fmt_dose, new_canvas, finish...
NAME = "My design"           # shown in the UI
ORDER = 4                    # optional sort position

def render(data):            # data: dict of the form fields (+ dose, seal_date)
    im, d = new_canvas()     # 1-bit 400x640, fontmode "1" (no anti-aliasing)
    d.text((24, 24), val(data, "coffee_name"), font=font(40), fill=0)
    return finish(im)        # asserts mode "1" and 400x640
```
Use `val(data, key)` so empty fields are omitted, and keep ~24 px margins. Run `python -m labelapp.samples` to preview.
