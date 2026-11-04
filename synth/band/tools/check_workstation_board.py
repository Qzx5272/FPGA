"""Exercise the same source-3 packets as Android on a physical FPGA via PC UART."""
from pathlib import Path
import json,sys,time
import serial
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from protocol import Event,Decoder,status

def run(build,port='COM12'):
    decoder=Decoder();evidence={}
    with serial.Serial(port,1000000,timeout=.018) as link:
        link.set_buffer_size(rx_size=65536,tx_size=8192)
        def send(e):
            time.sleep(.035);link.write(e.encode_uart());return decoder.feed(link.read(4096))
        def ask(e,k,predicate=lambda r:True):
            for _ in range(50):
                for raw in send(e):
                    if raw[1]==k and predicate(raw):return raw
            raise RuntimeError(f'No matching response {k:x}')
        def word(raw,start,n):return int.from_bytes(raw[start:start+n],'little')
        assert word(ask(Event(18),161),4,4)==0x20261107
        try:
            send(Event(10,parameter=18))
            send(Event(23,source=3,part=4,flags=3,parameter=0))
            cfg=lambda:ask(Event(20),163)
            initial=ask(Event(20),163,lambda r:r[5]==3 and r[10]==16)
            token=word(initial,11,2);assert initial[2]==4
            frozen=status(ask(Event(6),129))['song_sample']
            send(Event(22,source=2,contact=1,serial=token))
            now=status(ask(Event(6),129))['song_sample'];assert now==frozen
            send(Event(22,source=2,contact=0,serial=token))
            advanced=ask(Event(6),129,lambda r:status(r)['song_sample']>frozen)
            evidence['lesson']=[token,frozen,status(advanced)['song_sample']]
            send(Event(23,source=3,part=3,flags=2,parameter=1))
            evidence['solo']=list(ask(Event(20),163,lambda r:r[13]&16 and r[13]&7==1 and r[5]==0)[2:14])
            send(Event(23,source=3,part=3,flags=4,parameter=1))
            assert cfg()[13]&32
            ask(Event(6),129,lambda r:status(r)['song_sample']>0)
            send(Event(23,source=3,part=4,flags=1,parameter=0))
            raw=ask(Event(20,flags=77),164);frame=word(raw,2,2)
            chunks=[]
            for i in range(7):
                raw=ask(Event(20,flags=96+i),165,lambda r:r[3]==i and word(r,4,2)==frame)
                chunks.append(word(raw,6,20))
            evidence['visual_frame']=frame
            v=sum(x<<(160*i) for i,x in enumerate(chunks))
            assert v>>948 and (v>>436)&((1<<384)-1)
        finally:
            send(Event(5,flags=1));send(Event(10,parameter=64))
        assert decoder.bad_crc==0,decoder.bad_crc
    evidence['crc_errors']=decoder.bad_crc
    (build/'workstation_board.json').write_text(json.dumps(evidence,indent=2))
    print('PASS physical phone commands, guided transport, solo, ensemble and visual chunks')
if __name__=='__main__':run(Path(sys.argv[1]))
