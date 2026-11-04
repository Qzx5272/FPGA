"""Exercise the actual FPGA protocol. --sound plays a short low-volume test."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
import serial
from protocol import Controls,TelemetryParser,BAUD

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',default='COM12');ap.add_argument('--sound',action='store_true');args=ap.parse_args()
    c=Controls(volume=12 if args.sound else 0,attack_ms=2,release_ms=100)
    parser=TelemetryParser();seq=0;records=[]
    with serial.Serial(args.port,BAUD,timeout=.01,write_timeout=.2) as port:
        port.reset_input_buffer()
        def exchange(panic=False,timeout=.3):
            nonlocal seq
            sent=seq;seq=(seq+1)&255;start=time.monotonic();port.write(c.packet(sent,panic))
            while time.monotonic()-start<timeout:
                for r in parser.feed(port.read(100)):
                    if r['sequence']==sent:
                        r['rtt_ms']=round((time.monotonic()-start)*1000,2);records.append(r);return r
            raise RuntimeError('No valid FPGA reply on '+args.port)
        try:
            first=exchange(True)
            assert first['version']==2,first
            c.keys=0x20
            for _ in range(10):r=exchange();time.sleep(.025)
            assert r['keys']==32 and r['voices']==1,r
            if args.sound:assert r['peak']>0,r
            c.keys=255
            for _ in range(10):r=exchange();time.sleep(.025)
            assert r['keys']==255 and r['voices']==8,r
            c.keys=0
            for _ in range(10):r=exchange();time.sleep(.025)
            assert r['voices']==0,r
            c.keys=1;exchange();time.sleep(.6)
            # First reply after silence reports watchdog-cleared engine state.
            c.keys=0;r=exchange();assert r['voices']==0,r
            print('PASS hardware: state echo, 1/8 voices, release, watchdog'+(', nonzero audio peak' if args.sound else ' (muted)'))
        finally:
            c.keys=0;port.write(c.packet(seq,True))
    out=Path(__file__).resolve().parents[1]/'test-output/hardware.json';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(records[-1]))

if __name__=='__main__':main()
