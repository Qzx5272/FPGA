"""Confirm the selected band identity after a diagnostic SRAM run and stop it."""
import sys,time,json,hashlib,datetime
from pathlib import Path
import serial
band=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(band/'host'))
from protocol import Event,Decoder,status
selected=json.loads((band/'CURRENT_RELEASE.json').read_text())
release=band/'release'/selected['release']
manifest=json.loads((release/'manifest.json').read_text())
digest=hashlib.sha256((release/'starcluster_band.fs').read_bytes()).hexdigest()
assert digest==manifest['bitstream_sha256']
decoder=Decoder();capture=bytearray();identity=None;stopped=None
path=band/'evidence/restored_band_after_diagnostic.json'
path.write_text(json.dumps(dict(status='running',time=datetime.datetime.now().isoformat(),bitstream_sha256=digest),indent=2))
with serial.Serial('COM12',1000000,timeout=.01,write_timeout=.2) as port:
    def send(e):
        data=e.encode_uart()
        if port.write(data)!=len(data):raise IOError('Short write')
        time.sleep(.005)
    def read():
        b=port.read(4096);capture.extend(b);return decoder.feed(b)
    until=time.monotonic()+3
    while identity is None and time.monotonic()<until:
        send(Event(18))
        for f in read():
            if f[1]==161:identity=dict(build_id=int.from_bytes(f[4:8],'little'),capacity=int.from_bytes(f[8:12],'little'))
    if identity!=dict(build_id=manifest['build_id'],capacity=256):raise RuntimeError('Restored identity mismatch: '+repr(identity))
    send(Event(127));send(Event(10,parameter=0));send(Event(5,flags=1))
    until=time.monotonic()+3
    while stopped is None and time.monotonic()<until:
        send(Event(6))
        for f in read():
            if f[1] in (128,129):
                s=status(f)
                if not s['playing'] and s['voices']==0:stopped=s
    if stopped is None or decoder.bad_crc:
        failure=dict(status='failed',time=datetime.datetime.now().isoformat(),bitstream_sha256=digest,identity=identity,stopped=stopped,bad_crc=decoder.bad_crc)
        path.write_text(json.dumps(failure,indent=2));path.with_suffix('.raw').write_bytes(capture)
        raise RuntimeError('Stop acknowledgement or CRC failed: '+repr(failure))
record=dict(status='passed',time=datetime.datetime.now().isoformat(),bitstream_sha256=digest,
    identity=identity,stopped=stopped,requested_master_gain=0,bad_crc=decoder.bad_crc,
    note='SRAM restoration; no Flash write or analog sound measurement')
path.write_text(json.dumps(record,indent=2));path.with_suffix('.raw').write_bytes(capture)
print(json.dumps(record,indent=2))
