"""On-board v2 transport/voice integration test; briefly emits low-level audio."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
import serial
from protocol import Controls,TelemetryParser,BAUD
c=Controls(volume=12,attack_ms=2,release_ms=80)
parser=TelemetryParser(); seq=0;records=[]
with serial.Serial('COM12',BAUD,timeout=.01,write_timeout=.2) as port:
    port.reset_input_buffer()
    def exchange(panic=False):
        global seq
        sent=seq;seq=(seq+1)&255;port.write(c.packet(sent,panic))
        deadline=time.monotonic()+.5
        while time.monotonic()<deadline:
            for r in parser.feed(port.read(100)):
                if r['sequence']==sent:
                    assert r['version']==2,r
                    records.append(r);return r
        raise RuntimeError('No matching v2 telemetry')
    def collect(seconds):
        batch=[];end=time.monotonic()+seconds
        while time.monotonic()<end:
            batch.append(exchange());time.sleep(.03)
        return batch
    try:
        exchange(True)
        c.auto_play=True
        auto=collect(1.2)
        assert max(r['voices'] for r in auto)>=3,auto
        assert max(r['peak'] for r in auto)>0,auto
        c.tone=3;c.brightness=8;c.keys=1
        duet=collect(1.4)
        assert max(r['voices'] for r in duet)>=4,duet
        c.brightness=0
        vowel=collect(.6)
        assert max(r['voices'] for r in vowel)>=2,vowel
        c.keys=0;c.auto_play=False;exchange(True)
        stopped=collect(.2)
        assert all(r['voices']==0 and r['peak']==0 for r in stopped[1:]),stopped
        c.tone=0;c.auto_play=True;collect(.2)
        time.sleep(.65)
        c.auto_play=False
        watchdog=exchange()
        assert watchdog['voices']==0,watchdog
    finally:
        c.keys=0;c.auto_play=False;port.write(c.packet(seq,True))
out=Path(__file__).resolve().parents[1]/'test-output/duet_hardware.json'
out.write_text(json.dumps({'auto':auto,'duet':duet,'vowel':vowel,'stop':stopped,'watchdog':watchdog},indent=2))
print('PASS hardware v2: FPGA auto accompaniment, concurrent greeting/vowel, panic, watchdog')
