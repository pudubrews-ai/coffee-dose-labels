import asyncio
from bleak import BleakScanner, BleakClient
CMDS=[("battery 1F1108",b"\x1f\x11\x08"),("paper 1F1111",b"\x1f\x11\x11"),("fw 1F1107",b"\x1f\x11\x07"),
("1F1113",b"\x1f\x11\x13"),("timer 1F110E",b"\x1f\x11\x0e"),("serial 1F1109",b"\x1f\x11\x09"),
("DLE EOT1 100401",b"\x10\x04\x01"),("DLE EOT4 100404",b"\x10\x04\x04")]
async def main():
    print("scanning 10s",flush=True)
    devs=await BleakScanner.discover(timeout=10,return_adv=True)
    cand=None
    for a,(d,adv) in devs.items():
        print(a,d.name,adv.local_name,adv.rssi,adv.service_uuids,flush=True)
        if (d.name or adv.local_name or "").upper().startswith(("Q","T02","M0","PHOMEMO")): cand=d
    if not cand: print("no candidate"); return
    print("candidate",cand,flush=True)
    async with BleakClient(cand,timeout=20) as c:
        notif=[]
        for s in c.services:
            print("SVC",s.uuid)
            for ch in s.characteristics:
                print("  CH",ch.uuid,ch.properties,flush=True)
                if "read" in ch.properties:
                    try: print("    read:",(await c.read_gatt_char(ch)).hex())
                    except Exception as e: print("    read err",e)
        def mk(u): return lambda _,d: print("  NOTIFY",u,bytes(d).hex(),flush=True)
        for s in c.services:
            for ch in s.characteristics:
                if "notify" in ch.properties or "indicate" in ch.properties:
                    try: await c.start_notify(ch,mk(ch.uuid)); print("subscribed",ch.uuid)
                    except Exception as e: print("sub err",ch.uuid,e)
        w=[ch for s in c.services for ch in s.characteristics if "write" in ch.properties or "write-without-response" in ch.properties]
        for ch in w:
            print("== writing to",ch.uuid,ch.properties,flush=True)
            for n,cmd in CMDS:
                try:
                    await c.write_gatt_char(ch,cmd,response="write" in ch.properties); print(n,"sent",flush=True)
                except Exception as e: print(n,"write err",e)
                await asyncio.sleep(1.2)
asyncio.run(asyncio.wait_for(main(),90))
