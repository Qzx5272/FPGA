"""Identity-checked stop/mute and digital zero-voice readback; no gain readback."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

import serial

band = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(band / 'host'))
from protocol import Event, Decoder, status

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--release', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
ap.add_argument('--port', default='COM12')
a = ap.parse_args()
if a.output.exists() or a.output.with_suffix('.raw').exists():
    raise RuntimeError('Preserve previous cleanup evidence')
m = json.loads((a.release / 'manifest.json').read_text(encoding='utf-8'))
assert hashlib.sha256((a.release / 'starcluster_band.fs').read_bytes()).hexdigest() == m['bitstream_sha256']
assert m.get('build_id')
a.output.parent.mkdir(parents=True, exist_ok=True)
record = dict(status='running', started=datetime.datetime.now().isoformat(),
              build_id=m['build_id'], bitstream_sha256=m['bitstream_sha256'],
              master_zero_command_sent=False, gain_readback_available=False,
              driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
decoder = Decoder()
raw = bytearray()
try:
    with serial.Serial(a.port, 1000000, timeout=.02, write_timeout=.2) as port:
        def exchange(event):
            data = event.encode_uart()
            if port.write(data) != len(data):
                raise IOError('Short UART write')
            time.sleep(.03)
            block = port.read(8192)
            raw.extend(block)
            return decoder.feed(block)

        matched = False
        until = time.monotonic() + 4
        while time.monotonic() < until and not matched:
            for frame in exchange(Event(18)):
                if frame[1] == 161:
                    actual = int.from_bytes(frame[4:8], 'little')
                    if actual != m['build_id']:
                        raise RuntimeError('Unexpected FPGA build; no control commands sent')
                    matched = True
        if not matched:
            raise RuntimeError('No verified build identity; no control commands sent')
        exchange(Event(5, flags=1))
        exchange(Event(127))
        exchange(Event(10, parameter=0))
        record['master_zero_command_sent'] = True
        until = time.monotonic() + 4
        while time.monotonic() < until and record['status'] != 'passed':
            for frame in exchange(Event(6)):
                if frame[1] in (128, 129):
                    s = status(frame)
                    record['last_status'] = s
                    if not s['playing'] and s['voices'] == 0:
                        record['status'] = 'passed'
        if record['status'] != 'passed' or decoder.bad_crc:
            raise RuntimeError('Missing clean stopped/zero-voice readback')
except Exception as error:
    record.update(status='failed', error=str(error))
    raise
finally:
    record.update(finished=datetime.datetime.now().isoformat(), crc_errors=decoder.bad_crc)
    a.output.write_text(json.dumps(record, indent=2), encoding='utf-8')
    a.output.with_suffix('.raw').write_bytes(raw)
    a.output.with_suffix('.driver.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(record, indent=2))
