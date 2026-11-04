"""Select each built-in ROM through the physical board UART and verify playback."""
import argparse
import json
import time
from pathlib import Path
import serial
from rehearsal_rom import FILES, BAND, load
from protocol import Event, Decoder, status

def run(build, port):
    decoder=Decoder()
    results=[]
    with serial.Serial(port,1000000,timeout=.04) as link:
        link.set_buffer_size(rx_size=65536,tx_size=8192)
        def event(kind,**fields):
            time.sleep(.035)
            link.write(Event(kind,source=1,**fields).encode_uart())
        def collect():
            chunk=link.read(2048)
            before=bytes(decoder.buffer)
            count=decoder.bad_crc
            frames=decoder.feed(chunk)
            if decoder.bad_crc!=count:
                with (build/'uart_fault_capture.bin').open('ab') as log:log.write(before+chunk)
                print('CRC at',time.monotonic(), 'received',len(chunk),'queued',link.in_waiting,flush=True)
            return frames
        def query(kind,reply,accept,timeout=5):
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                event(kind)
                for raw in collect():
                    if raw[1] in reply and accept(raw):return raw
            raise TimeoutError((kind,reply))
        identity=json.loads((build/'manifest.json').read_text())['build_id']
        query(18,[161],lambda r:int.from_bytes(r[4:8],'little')==identity)
        link.write(Event(20,source=1,flags=77).encode_uart())
        saved=next((int.from_bytes(r[4:20],'little') for r in collect() if r[1]==164),None)
        level=(saved>>1)&127 if saved is not None else 64
        event(10,parameter=18);collect()
        try:
            for i,name in enumerate(FILES):
                score=load(BAND/'assets'/(name+'.json'))
                expected=len(score['events']),round(score['duration_samples']*120/score.get('performance',{}).get('tempo',120))
                print("Select",i+1,flush=True);event(23,parameter=i);collect()
                def stored(r):
                    return (int.from_bytes(r[16:20],'little'),int.from_bytes(r[20:24],'little'))==expected and int.from_bytes(r[12:16],'little')==0
                query(14,[160],stored)
                reply=status(query(6,[129],lambda r:status(r)['voices']>0 and status(r)['song_sample']>0))
                assert reply['deadline_miss']==0 and reply['clips']==0,reply
                results.append(dict(song=i+1,title=score['title'],events=expected[0],samples=expected[1],playing=reply))
        finally:
            event(23,parameter=0);end=time.monotonic()+.3
            while time.monotonic()<end:collect()
            event(5,flags=1);collect();event(10,parameter=level)
            query(6,[128],lambda r:not status(r)['playing'])
    assert decoder.bad_crc==0,decoder.bad_crc
    (build/'five_song_board_check.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
    print('PASS five ROM selections, exact score counts/durations, active voices, transport stopped, zero CRC errors')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--port',default='COM12');a=p.parse_args()
    run(a.build,a.port)
