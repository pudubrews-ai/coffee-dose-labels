"""Phomemo M221 BLE driver. CLI: python -m labelapp.printer status | print IMAGE.png"""
import asyncio
import sys
from PIL import Image
from bleak import BleakClient, BleakScanner
from . import config as C

DENSITY = 5
HEAT = {1: 40, 2: 60, 3: 80, 4: 100, 5: 120, 6: 140, 7: 160, 8: 200}[DENSITY]
FEED = 32
CHUNK, DELAY = 128, 0.02
COPY_PAUSE = 1.0


class PrinterError(Exception):
    pass


def image_to_raster(im: Image.Image) -> bytes:
    """400x640 image -> 576-wide, 1=black, MSB-first, 72 bytes/row."""
    if im.size != (C.LABEL_W, C.LABEL_H):
        raise PrinterError(f"image must be {C.LABEL_W}x{C.LABEL_H}, got {im.size}")
    pad = Image.new("1", (C.HEAD_PX, C.LABEL_H), 1)
    pad.paste(im.convert("1", dither=Image.Dither.NONE), ((C.HEAD_PX - C.LABEL_W) // 2, 0))
    inv = pad.convert("L").point(lambda v: 255 if v < 128 else 0).convert("1")
    data = inv.tobytes()
    assert len(data) == 72 * C.LABEL_H
    return data


def build_job(data: bytes) -> list[bytes]:
    h = C.LABEL_H
    return [
        bytes([0x1b, 0x40]),
        bytes([0x1b, 0x37, 7, HEAT, 2]),
        bytes([0x1d, 0x7c, DENSITY]),
        bytes([0x1d, 0x76, 0x30, 0x00, 72, 0, h & 0xff, h >> 8]) + data,
        bytes([0x1b, 0x4a, FEED]),
    ]


class Printer:
    def __init__(self):
        self.client: BleakClient | None = None
        self.notes: list[bytes] = []
        self.lock = asyncio.Lock()      # one job / BLE operation at a time
        self.printing = False
        self.progress = {"state": "idle", "done": 0, "total": 0, "message": ""}

    def _cb(self, _, b):
        self.notes.append(bytes(b))

    @property
    def connected(self):
        return bool(self.client and self.client.is_connected)

    async def _find(self):
        def match(d, adv):
            return (d.name == C.PRINTER_NAME or adv.local_name == C.PRINTER_NAME
                    or C.PRINTER_SERVICE_UUID in [u.lower() for u in adv.service_uuids])
        dev = await BleakScanner.find_device_by_filter(match, timeout=12)
        if not dev:
            raise PrinterError("Printer not found. Is it switched on and in range?")
        return dev

    async def connect(self):
        if self.connected:
            return
        await self.disconnect()
        dev = await self._find()
        c = BleakClient(dev, timeout=20)
        try:
            await c.connect()
            await c.start_notify(C.NOTIFY_CHAR, self._cb)
        except Exception as e:
            try: await c.disconnect()
            except Exception: pass
            raise PrinterError(f"Could not connect to printer: {e}")
        self.client = c

    async def disconnect(self):
        c, self.client = self.client, None
        if c:
            try: await c.disconnect()
            except Exception: pass

    async def _write(self, data: bytes):
        for i in range(0, len(data), CHUNK):
            await self.client.write_gatt_char(C.WRITE_CHAR, data[i:i + CHUNK], response=False)
            await asyncio.sleep(DELAY)

    async def _query(self, cmd: bytes, kind: int, timeout=2.0) -> bytes | None:
        """Send a 1F 11 xx query, return the payload of the matching 1a <kind> reply."""
        for _ in range(2):                       # one retry if the reply is lost
            self.notes.clear()
            await self.client.write_gatt_char(C.WRITE_CHAR, cmd, response=False)
            end = asyncio.get_event_loop().time() + timeout
            while asyncio.get_event_loop().time() < end:
                for n in self.notes:
                    if len(n) >= 3 and n[0] == 0x1a and n[1] == kind:
                        return n[2:]
                await asyncio.sleep(0.05)
        return None

    async def _status_raw(self) -> dict:
        bat = await self._query(b"\x1f\x11\x08", 0x04)
        pap = await self._query(b"\x1f\x11\x11", 0x06)
        tmp = await self._query(b"\x1f\x11\x13", 0x03)
        s = {"connected": True, "battery": None, "low_battery": False,
             "paper": None, "hot": None, "error": None}
        if bat:
            if 0xa1 <= bat[0] <= 0xa4:
                s["low_battery"] = True
            else:
                s["battery"] = bat[0]
        if pap:
            s["paper"] = pap[0] == 0x89
        if tmp:
            s["hot"] = tmp[0] == 0xa9
        return s

    async def status(self) -> dict:
        if self.printing or self.lock.locked():
            return {"connected": self.connected, "busy": True, "battery": None,
                    "paper": None, "hot": None, "error": None}
        async with self.lock:
            try:
                await self.connect()
                return await self._status_raw()
            except PrinterError as e:
                return {"connected": False, "error": str(e), "battery": None, "paper": None}
            except Exception as e:
                await self.disconnect()
                return {"connected": False, "error": f"{type(e).__name__}: {e}",
                        "battery": None, "paper": None}

    async def print_image(self, im: Image.Image, copies: int = 1) -> dict:
        data = image_to_raster(im)
        job = build_job(data)
        if self.lock.locked():
            raise PrinterError("Printer is busy with another job.")
        async with self.lock:
            self.printing = True
            self.progress = {"state": "connecting", "done": 0, "total": copies, "message": "Connecting..."}
            try:
                await self.connect()
                for n in range(copies):
                    st = await self._status_raw()
                    if st["paper"] is False:
                        raise PrinterError(f"Out of paper after {n} of {copies} labels.")
                    if st["paper"] is None:
                        raise PrinterError("No paper status reply from printer.")
                    if st["hot"]:
                        raise PrinterError(f"Print head too hot after {n} of {copies} labels.")
                    self.progress.update(state="printing", message=f"Printing {n + 1} of {copies}...")
                    self.notes.clear()
                    for part in job:
                        await self._write(part)
                        await asyncio.sleep(0.1)
                    await asyncio.sleep(COPY_PAUSE if n < copies - 1 else 1.5)
                    self.progress["done"] = n + 1
                self.progress.update(state="done", message=f"Printed {copies} label(s).")
                return {"printed": copies, "notifications": {"acks": sum(n == b"\x01\x01" for n in self.notes),
                                                          "other": [n.hex() for n in self.notes if n != b"\x01\x01"]}}
            except PrinterError as e:
                self.progress.update(state="error", message=str(e)); raise
            except Exception as e:
                await self.disconnect()
                msg = f"Printing failed ({type(e).__name__}: {e}). {self.progress['done']} of {copies} printed."
                self.progress.update(state="error", message=msg)
                raise PrinterError(msg)
            finally:
                self.printing = False


printer = Printer()


async def _cli():
    import json
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(await printer.status(), indent=2))
    elif cmd == "print":
        im = Image.open(sys.argv[2]).convert("1")
        print(await printer.print_image(im, int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    else:
        print("usage: python -m labelapp.printer status | print IMAGE.png [copies]")
    await printer.disconnect()

if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(_cli(), 180))
