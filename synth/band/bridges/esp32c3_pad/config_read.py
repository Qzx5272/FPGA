"""Read-only vendor configuration capture through the C3 serial command interface."""
import argparse
import json
import time
from pathlib import Path
import serial

p=argparse.ArgumentParser()
p.add_argument('--port',default='COM8')
p.add_argument('--region',type=int,choices=[4,5],default=5)
p.add_argument('--address',type=int,default=0)
p.add_argument('--length',type=int,required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
assert 0<=a.address<65536 and 0<a.length<=65536-a.address
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
s=serial.Serial(port=None,baudrate=115200,timeout=.1);s.dtr=False;s.rts=False;s.port=a.port;s.open()
data=bytearray();frames=[]
with s, out.with_suffix('.log').open('w',encoding='utf-8') as log:
    s.reset_input_buffer()
    for address in range(a.address,a.address+a.length,1000):
        length=min(1000,a.address+a.length-address)
        s.write(f'read {a.region} {address} {length}\n'.encode())
        stream=bytearray();deadline=time.monotonic()+5;found=False
        while time.monotonic()<deadline and not found:
            line=s.readline().decode(errors='replace').strip()
            if not line:continue
            log.write(line+'\n');log.flush()
            if not line.startswith('CONFIG_RX '):continue
            stream.extend(bytes.fromhex(line.split('bytes=')[1]))
            while len(stream)>=7:
                if stream[:2]!=b'\x00\x59':raise ValueError('Bad vendor header')
                n=int.from_bytes(stream[3:6],'little')
                if n>2000:raise ValueError('Oversized frame')
                if len(stream)<n+7:break
                frame=bytes(stream[:n+7]);del stream[:n+7]
                payload=frame[6:-1]
                if (sum(payload)+frame[-1])&255 !=255:raise ValueError('Checksum mismatch')
                frames.append(frame.hex())
                if frame[2]!=0x23:continue
                if payload[:8]!=bytes([a.region])+address.to_bytes(4,'little')+length.to_bytes(3,'little'):
                    raise ValueError('Read response address/length mismatch')
                if len(payload)!=8+length:raise ValueError('Read response size mismatch')
                data.extend(payload[8:]);found=True;break
        if not found:raise TimeoutError(f'No matching reply at {address}')
        print(f'READ region={a.region} address={address} length={length} checksum=OK',flush=True)
out.write_bytes(data)
out.with_suffix('.json').write_text(json.dumps({'region':a.region,'address':a.address,'length':len(data),'frames':frames},indent=2))
