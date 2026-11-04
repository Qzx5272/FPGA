"""Check parameter voice mode on the attached board at low output level."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'host'))
import serial
from protocol import Controls,TelemetryParser
c=Controls(tone=3,brightness=0,volume=10,velocity=100,attack_ms=12,release_ms=70)
parser=TelemetryParser();seq=0;records=[]
with serial.Serial('COM12',115200,timeout=.02,write_timeout=.2) as port:
    port.reset_input_buffer()
    def exchange(panic=False):
        global seq
        sent=seq;seq=(seq+1)&255
        port.write(c.packet(sent,panic));start=time.monotonic()
        while time.monotonic()-start<.5:
            for reply in parser.feed(port.read(100)):
                if reply['sequence']==sent:
                    records.append(dict(unit=c.brightness,**reply));return reply
        raise RuntimeError('Voice command not acknowledged')
    try:
        exchange(True)
        for unit in range(8):
            c.brightness=unit;c.keys=1
            for _ in range(8):r=exchange();time.sleep(.025)
            assert r['voices']==1 and r['peak']>0,r
        c.keys=0
        for _ in range(8):r=exchange();time.sleep(.025)
        assert r['voices']==0 and r['peak']==0,r
        c.keys=1;exchange();time.sleep(.6)
        c.keys=0;r=exchange()
        assert r['voices']==0,r
    finally:
        c.keys=0;exchange(True)
(ROOT/'test-output/voice_hardware.json').write_text(json.dumps(records,indent=2)+'\n')
print('PASS hardware voice: eight units acknowledge, active/nonzero output, release, watchdog; listening quality not verified.')
