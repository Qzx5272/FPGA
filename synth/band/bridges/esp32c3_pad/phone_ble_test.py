"""Exercise the actual phone GATT service from a desktop BLE central.
Writes the already-confirmed blue value to the fixed demo pad (no color change).
"""
import asyncio,json,time
from bleak import BleakClient,BleakScanner
from pathlib import Path

SERVICE='4fafc201-1fb5-459e-8fcc-c5c9c331914b'
RX=SERVICE.replace('c201','c202');STATUS=SERVICE.replace('c201','c203')
async def main():
    device=await BleakScanner.find_device_by_filter(lambda d,a:SERVICE in a.service_uuids,timeout=15)
    if not device:raise RuntimeError('C3 phone service not discovered')
    print('FOUND',device,flush=True)
    records=[]
    async with BleakClient(device,timeout=20) as c:
        await c.start_notify(STATUS,lambda _,v:records.append({'at':time.time(),'hex':bytes(v).hex()}))
        initial=bytes(await c.read_gatt_char(STATUS));print('INITIAL',initial.hex(),flush=True)
        assert len(initial)==20 and initial[:2]==b'\x53\x01'
        assert initial[2:4]==b'\x01\x01','Pad not ready'
        ident=(initial[4]+1)%256
        # Invalid checksum must not initiate a configuration transaction.
        bad=bytes([0x53,1,ident,1,0,0,250,0])
        await c.write_gatt_char(RX,bad,response=True);await asyncio.sleep(.6)
        after=bytes(await c.read_gatt_char(STATUS));assert after[4]==initial[4]
        p=bytearray([0x53,1,ident,1,0,0,250,0]);p[-1]=(~sum(p[:-1]))&255
        await c.write_gatt_char(RX,p,response=True)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            await asyncio.sleep(.3);result=bytes(await c.read_gatt_char(STATUS))
            if result[4]==ident and result[5] not in (0,1):break
        else:raise TimeoutError('No final reply')
        print('RESULT',result.hex(),flush=True);assert result[5]==2,result.hex()
        assert result[2:4]==b'\x01\x01' and result[6:9]==bytes([0,0,250])
        await asyncio.sleep(3)
    async with BleakClient(device,timeout=20) as c:
        result=bytes(await c.read_gatt_char(STATUS));assert result[2:4]==b'\x01\x01'
        print('RECONNECT_OK',result.hex(),flush=True)
    Path('synth/band/evidence/c3_phone_20261031/ble_test.json').write_text(json.dumps(records,indent=2))
    print('PASS malformed request rejected; model/write/readback; concurrent pad link; central reconnect',flush=True)
asyncio.run(main())
