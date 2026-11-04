"""Read-only identity polling with a raw capture for link-error diagnosis."""
import sys,time,json,zlib,datetime,threading
from pathlib import Path
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
import serial
from protocol import Event,Decoder
decoder=Decoder();data=bytearray();frames=[]
guard=int(sys.argv[sys.argv.index('--guard')+1]) if '--guard' in sys.argv else 0
batch=int(sys.argv[sys.argv.index('--batch')+1]) if '--batch' in sys.argv else 0
packet=Event(18).encode()+bytes(guard)
with serial.Serial('COM12',1000000,timeout=.005,write_timeout=.1) as port:
    port.set_buffer_size(rx_size=65536,tx_size=65536)
    port.reset_input_buffer()
    count=int(sys.argv[sys.argv.index('--count')+1]) if '--count' in sys.argv else 100 if '--burst' in sys.argv else 1000
    def receive():
        block=port.read(4096);data.extend(block);frames.extend(decoder.feed(block))
    if '--burst' in sys.argv:
        stop=threading.Event();errors=[]
        def reader():
            try:
                while not stop.is_set():receive()
            except Exception as e:errors.append(repr(e))
        worker=threading.Thread(target=reader);worker.start()
        try:
            for i in range(count):
                port.write(packet)
                if batch and (i+1)%batch==0:time.sleep(.005)
            pending_after_write=port.out_waiting
            until=time.monotonic()+5
            while time.monotonic()<until:
                if guard and len(frames)>=count:break
                time.sleep(.01)
        finally:stop.set();worker.join()
        if errors:raise RuntimeError(errors)
    else:
        for i in range(count):
            port.write(packet);until=time.monotonic()+.02
            while time.monotonic()<until:receive()
expected=count if guard or '--burst' not in sys.argv else None
report=dict(status='passed' if frames and decoder.bad_crc==0 and (expected is None or len(frames)==expected) else 'failed',mode='burst' if '--burst' in sys.argv else 'paced',batch_per_5ms=batch,concurrent_receive='--burst' in sys.argv,queued_tx_bytes_after_writes=pending_after_write if '--burst' in sys.argv else 0,guard_bytes=guard,requests=count,valid_frames=len(frames),bad_crc=decoder.bad_crc,unique_frames=len(set(frames)),
            identities=[f.hex() for f in sorted(set(frames))][:10],bytes=len(data))
name='link_probe_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
(band/'evidence'/(name+'.raw')).write_bytes(data)
(band/'evidence'/(name+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
