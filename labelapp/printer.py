"""Phomemo M220/M221 BLE driver. CLI: python -m labelapp.printer status | print IMAGE.png"""
import asyncio
import json
import os
import re
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
        self.selected_id: str | None = None
        self.selected_name: str | None = None
        self._load_selection()
        self.notes: list[bytes] = []
        self.lock = asyncio.Lock()      # one job / BLE operation at a time
        self.printing = False
        self.progress = {"state": "idle", "done": 0, "total": 0, "message": ""}

    def _cb(self, _, b):
        self.notes.append(bytes(b))

    @property
    def connected(self):
        return bool(self.client and self.client.is_connected)

    def _load_selection(self):
        try:
            with open(C.STATE_FILE) as f:
                j = json.load(f)
            if isinstance(j.get("id"), str) and j["id"]:
                self.selected_id, self.selected_name = j["id"], j.get("name")
        except (OSError, ValueError, AttributeError):
            pass

    async def select(self, pid: str | None, name: str | None = None):
        """Choose the printer to use (persisted). Drops any link to a previously selected one."""
        pid = (pid or "").strip() or None
        if self.printing:
            raise PrinterError("Printer is busy with a job. Try again when it finishes.")
        async with self.lock:
            if pid != self.selected_id:
                await self.disconnect()
            self.selected_id, self.selected_name = pid, name
        try:
            os.makedirs(C.STATE_DIR, exist_ok=True)
            if pid:
                with open(C.STATE_FILE, "w") as f:
                    json.dump({"id": pid, "name": name}, f)
            elif os.path.exists(C.STATE_FILE):
                os.remove(C.STATE_FILE)
        except OSError:
            pass                                   # selection still works for this run

    @staticmethod
    def is_candidate(name: str | None, services) -> bool:
        if any(u.lower() in C.ADV_SERVICES for u in services or []):
            return True
        return bool(name and (re.match(C.NAME_PATTERN, name) or "phomemo" in name.lower()))

    async def scan(self, timeout: float = 6.0) -> list[dict]:
        """BLE scan for Phomemo-like devices -> [{id, name, rssi}], strongest first."""
        found = await BleakScanner.discover(timeout=timeout, return_adv=True)
        out = {}
        for addr, (d, adv) in found.items():
            name = d.name or adv.local_name
            if self.is_candidate(name, adv.service_uuids):
                out[addr] = {"id": addr, "name": name or "Unnamed printer", "rssi": adv.rssi}
        if self.connected and self.selected_id and self.selected_id not in out:
            # a connected printer stops advertising, so it would vanish from the scan
            out[self.selected_id] = {"id": self.selected_id, "name": self.selected_name or "Printer", "rssi": None}
        return sorted(out.values(), key=lambda x: -(x["rssi"] if x["rssi"] is not None else 0))

    async def _find(self):
        if not self.selected_id:
            raise PrinterError("No printer selected. Choose one with Scan.")
        dev = await BleakScanner.find_device_by_address(self.selected_id, timeout=12)
        if not dev:
            raise PrinterError("Selected printer not found. Is it switched on and in range? Try Scan.")
        return dev

    async def connect(self):
        if self.connected:
            return
        await self.disconnect()
        dev = await self._find()
        c = BleakClient(dev, timeout=20)
        try:
            await c.connect()
            chars = {ch.uuid.lower() for sv in c.services if sv.uuid.lower() == C.GATT_SERVICE for ch in sv.characteristics}
            if C.WRITE_CHAR not in chars or C.NOTIFY_CHAR not in chars:
                raise PrinterError("This device is not a compatible Phomemo (no ff00 service with ff02/ff03).")
            await c.start_notify(C.NOTIFY_CHAR, self._cb)
        except PrinterError:
            try: await c.disconnect()
            except Exception: pass
            raise
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

    @staticmethod
    def _no_reply(s: dict) -> bool:
        return s["battery"] is None and not s["low_battery"] and s["paper"] is None and s["hot"] is None

    async def _status_locked(self) -> dict:
        async with self.lock:
            if self.printing:
                return self._busy()
            try:
                await self.connect()
                s = await self._status_raw()
                if self._no_reply(s):          # link looks up but the printer is asleep/gone
                    await self.disconnect()
                    return {"connected": False, "error": "Printer not responding. Switch it on and try again.",
                            "battery": None, "paper": None}
                return s
            except PrinterError as e:
                return {"connected": False, "error": str(e), "battery": None, "paper": None}
            except Exception as e:
                await self.disconnect()
                return {"connected": False, "error": f"{type(e).__name__}: {e}",
                        "battery": None, "paper": None}

    def _busy(self) -> dict:
        return {"connected": self.connected, "busy": True, "battery": None,
                "paper": None, "hot": None, "error": None}

    async def status(self) -> dict:
        if self.printing:
            return self._busy()
        t = getattr(self, "_status_task", None)
        if t is None or t.done():              # concurrent status calls share one in-flight query
            t = self._status_task = asyncio.ensure_future(self._status_locked())
        return await asyncio.shield(t)

    async def print_image(self, im: Image.Image, copies: int = 1) -> dict:
        data = image_to_raster(im)
        job = build_job(data)
        if self.printing:
            raise PrinterError("Printer is busy with another job.")
        async with self.lock:                  # waits out any in-flight status poll
            self.printing = True
            self.progress = {"state": "connecting", "done": 0, "total": copies, "message": "Connecting..."}
            try:
                await self.connect()
                acks, other = 0, []
                for n in range(copies):
                    st = await self._status_raw()
                    if n == 0 and st["paper"] is None:      # stale link: reconnect and retry once
                        await self.disconnect()
                        await self.connect()
                        st = await self._status_raw()
                    if st["paper"] is False:
                        raise PrinterError(f"Out of paper after {n} of {copies} labels.")
                    if st["paper"] is None:
                        await self.disconnect()
                        raise PrinterError("No paper status reply from printer. Check it is on, then retry.")
                    if st["hot"]:
                        raise PrinterError(f"Print head too hot after {n} of {copies} labels.")
                    self.progress.update(state="printing", message=f"Printing {n + 1} of {copies}...")
                    self.notes.clear()
                    for part in job:
                        await self._write(part)
                        await asyncio.sleep(0.1)
                    await asyncio.sleep(COPY_PAUSE if n < copies - 1 else 1.5)
                    acks += sum(x == b"\x01\x01" for x in self.notes)
                    other += [x.hex() for x in self.notes if x != b"\x01\x01"]
                    self.progress["done"] = n + 1
                self.progress.update(state="done", message=f"Printed {copies} label(s).")
                return {"printed": copies, "notifications": {"acks": acks, "other": other}}
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
    if cmd == "scan":
        print(json.dumps(await printer.scan(), indent=2))
    elif cmd == "status":
        print(json.dumps(await printer.status(), indent=2))
    elif cmd == "print":
        im = Image.open(sys.argv[2]).convert("1")
        print(await printer.print_image(im, int(sys.argv[3]) if len(sys.argv) > 3 else 1))
    else:
        print("usage: python -m labelapp.printer status | print IMAGE.png [copies]")
    await printer.disconnect()

if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(_cli(), 180))
