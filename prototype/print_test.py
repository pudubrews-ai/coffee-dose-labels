"""Print ONE test label to Phomemo M221 over BLE. Sequence from phomymo printer.js printBLE() (m-series)."""
import asyncio, sys, os
from PIL import Image, ImageDraw, ImageFont
from bleak import BleakScanner, BleakClient

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "YOUR-PRINTER-BLE-NAME"
WR = "0000ff02-0000-1000-8000-00805f9b34fb"
NT = "0000ff03-0000-1000-8000-00805f9b34fb"
W, H, ROW = 400, 640, 576
DENSITY = 5          # phomymo scale 1-8 -> heat time 120
HEAT = {1:40,2:60,3:80,4:100,5:120,6:140,7:160,8:200}[DENSITY]
FEED = 32
CHUNK, DELAY = 128, 0.02

def font(size, bold=True):
    return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size, index=1 if bold else 0)

def render():
    im = Image.new("1", (W, H), 1)   # 1 = white
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    m = 16
    d.rectangle([m, m, W-1-m, H-1-m], outline=0, width=3)
    for k in range(1, 5):            # top ticks every 10 mm (80 px)
        x = 80*k; d.line([x, m+3, x, m+3+(14 if k % 5 else 14)], fill=0, width=2)
    for k in range(1, 8):            # left ticks
        y = 80*k; d.line([m+3, y, m+3+14, y], fill=0, width=2)
    # TOP arrow
    cx = W//2
    d.polygon([(cx, 36), (cx-22, 70), (cx+22, 70)], fill=0)
    d.rectangle([cx-7, 70, cx+7, 90], fill=0)
    f = font(30); t = "TOP"; w = d.textlength(t, font=f)
    d.text((cx-w/2, 96), t, font=f, fill=0)
    def centered(t, y, size, bold=True, maxw=340):
        while True:
            f = font(size, bold)
            if d.textlength(t, font=f) <= maxw: break
            size -= 1
        d.text((cx-d.textlength(t, font=f)/2, y), t, font=f, fill=0)
    centered("PUDU", 140, 90, maxw=330)
    centered("BREWS", 235, 90, maxw=330)
    centered("M221 test print", 350, 30, True)
    centered("50 x 80 mm", 392, 30, True)
    centered("2026-11-23", 434, 30, True)
    # density test lines 1-4 px
    y = 490
    for th in (1, 2, 3, 4):
        d.rectangle([50, y, 250, y+th-1], fill=0); y += th + 8
    # checkerboard 10 cells of 6 px, 6x6
    cs, ox, oy = 6, 280, 490
    for r in range(6):
        for c in range(10 if False else 6):
            if (r+c) % 2 == 0:
                d.rectangle([ox+c*cs, oy+r*cs, ox+c*cs+cs-1, oy+r*cs+cs-1], fill=0)
    d.text((50, 580), "density 1 2 3 4 px", font=font(18, False), fill=0)
    assert im.mode == "1"
    return im

def raster(im):
    pad = Image.new("1", (ROW, H), 1)
    pad.paste(im, ((ROW-W)//2, 0))
    pad.save(os.path.join(HERE, "raster_preview.png"))
    inv = pad.convert("L").point(lambda v: 255 if v < 128 else 0).convert("1")  # 1 bit = black
    return inv.tobytes()   # MSB-first, row-major, 72 bytes/row

def build_job(data):
    return [
        bytes([0x1b, 0x40]),                                  # INIT
        bytes([0x1b, 0x37, 7, HEAT, 2]),                      # ESC 7 heat
        bytes([0x1d, 0x7c, DENSITY]),                         # GS | density
        bytes([0x1d, 0x76, 0x30, 0x00, 72, 0, H & 0xff, H >> 8]) + data,
        bytes([0x1b, 0x4a, FEED]),                            # ESC J feed
    ]

async def main():
    im = render(); im.save(os.path.join(HERE, "test_label.png"))
    data = raster(im); assert len(data) == 72*H, len(data)
    if "--render-only" in sys.argv: print("rendered", len(data)); return
    print("scanning", flush=True)
    dev = await BleakScanner.find_device_by_name(NAME, timeout=15)
    if not dev: print("device not found"); return
    notes = []
    async with BleakClient(dev, timeout=20) as c:
        def cb(_, b): notes.append(bytes(b).hex()); print("NOTIFY", bytes(b).hex(), flush=True)
        await c.start_notify(NT, cb)
        await c.write_gatt_char(WR, bytes([0x1f, 0x11, 0x11]), response=False)
        await asyncio.sleep(1.0)
        paper = [n for n in notes if n.startswith("1a06")]
        if not paper or paper[-1] != "1a0689":
            print("ABORT: paper status", paper); return
        print("paper ok; sending job", flush=True)
        job = build_job(data)
        for part in job:
            for i in range(0, len(part), CHUNK):
                await c.write_gatt_char(WR, part[i:i+CHUNK], response=False)
                await asyncio.sleep(DELAY)
            await asyncio.sleep(0.1)
        print("sent; waiting 3s", flush=True)
        await asyncio.sleep(3)
        await c.stop_notify(NT)
    print("all notifications:", notes)
asyncio.run(asyncio.wait_for(main(), 120))
