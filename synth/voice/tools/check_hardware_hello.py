"""Verify board-owned phrase timing, completion and panic; low-volume audition."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host'))
import serial
from protocol import Controls,TelemetryParser
c=Controls(tone=3,brightness=8,volume=12,velocity=100)
parser=TelemetryParser();seq=0;records=[]
with serial.Serial('COM12',115200,timeout=.01,write_timeout=.2) as port:
    port.reset_input_buffer()
    def exchange(panic=False):
        global seq
        sent=seq;seq=(seq+1)&255;port.write(c.packet(sent,panic));start=time.monotonic()
        while time.monotonic()-start<.5:
            for r in parser.feed(port.read(100)):
                if r['sequence']==sent:
                    records.append(dict(unit=c.brightness,**r));return r
        raise RuntimeError('No acknowledgement')
    try:
        for mode,duration in [(8,1.28),(9,1.92)]:
            c.brightness=mode;c.keys=0;exchange(True);time.sleep(.03)
            c.keys=1;exchange();start=time.monotonic();heard=False;last_active=0
            while time.monotonic()-start<duration+.25:
                r=exchange();elapsed=time.monotonic()-start
                heard|=r['peak']>0
                if r['voices']:last_active=elapsed
                time.sleep(.025)
            assert heard and r['voices']==0 and r['peak']==0,(mode,r)
            assert duration-.15<last_active<duration+.1,(mode,last_active)
        c.keys=0;exchange();time.sleep(.02);c.keys=1;exchange();time.sleep(.1)
        exchange(True);time.sleep(.03);c.keys=0;r=exchange()
        assert r['voices']==0 and r['peak']==0,r
        c.keys=1;exchange();time.sleep(.6);c.keys=0;r=exchange()
        assert r['voices']==0,r
    finally:
        c.keys=0;exchange(True)
(ROOT/'test-output/hello_hardware.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS board hello: normal/slow duration, nonzero signal, completion/no repeat, panic, watchdog. Intelligibility unverified.')
