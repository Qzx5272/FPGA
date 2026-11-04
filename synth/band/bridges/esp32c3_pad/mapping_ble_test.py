"""No-change key mapping test: profile4/bank2/key5 stays MIDI24.
Requires the configuration backup to confirm this target before running.
"""
import asyncio,json,time
from pathlib import Path
from bleak import BleakClient,BleakScanner
SERVICE='4fafc201-1fb5-459e-8fcc-c5c9c331914b'
async def main():
    backup=Path('synth/band/evidence/c3_color_20261031/after_color.bin').read_bytes()
    base=3*2931+20*26
    assert backup[base]==0 and backup[base+2]==24
    d=await BleakScanner.find_device_by_filter(lambda d,a:SERVICE in a.service_uuids,timeout=8)
    if not d:raise RuntimeError('Not advertising: may already be connected to phone; do not interrupt phone')
    async with BleakClient(d) as c:
        assert c.services.get_characteristic(SERVICE.replace('c201','c204')) is not None
        status=SERVICE.replace('c201','c203');rx=SERVICE.replace('c201','c202')
        initial=bytes(await c.read_gatt_char(status));assert initial[2:4]==b'\1\1'
        ident=(initial[4]+1)%256;p=bytearray([0x53,1,ident,2,3,20,24,0]);p[7]=(~sum(p[:7]))&255
        await c.write_gatt_char(rx,p,response=True)
        for _ in range(50):
            await asyncio.sleep(.3);r=bytes(await c.read_gatt_char(status))
            if r[4]==ident and r[5]>1:break
        assert r[4]==ident and r[5]==2,r.hex()
        Path('synth/band/evidence/android_app_20261031/mapping_test.json').write_text(json.dumps({'request':p.hex(),'result':r.hex(),'target_note':24,'event_characteristic_present':True},indent=2))
        print('PASS mapping write + full 26-byte record readback; event characteristic present')
asyncio.run(main())
