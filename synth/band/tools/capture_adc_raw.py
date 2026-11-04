"""Read-only CH340 ADC capture; never opens the FPGA/JTAG serial ports."""
import argparse
import csv
import datetime
import json
from pathlib import Path
import re
import statistics
import time

import serial
from serial.tools import list_ports

p = argparse.ArgumentParser()
p.add_argument('--seconds', type=float, default=40)
p.add_argument('--port')
a = p.parse_args()
ports = [x for x in list_ports.comports() if (x.vid, x.pid) == (0x1A86, 0x7523)]
if a.port:
    ports = [x for x in ports if x.device.lower() == a.port.lower()]
if len(ports) != 1:
    raise SystemExit('Need exactly one ADC CH340 port; found: ' + repr([x.device for x in ports]))
out = Path(__file__).resolve().parents[3] / 'output' / 'adc_diagnostics' / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out.mkdir(parents=True, exist_ok=False)
samples, raw, pending = [], bytearray(), bytearray()
pattern = re.compile(rb'<v>:(\d\.\d{3}(?:,\d\.\d{3}){9})\r?\n')
port = serial.Serial(port=None, baudrate=460800, timeout=0.1)
port.dtr = False
port.rts = False
port.port = ports[0].device
port.open()
start = time.monotonic()
last_report = -5
print(f'Reading {port.port}, 460800 8N1 for {a.seconds}s; no commands sent.', flush=True)
try:
    while time.monotonic() - start < a.seconds:
        chunk = port.read(max(1, min(port.in_waiting, 4096)))
        raw.extend(chunk)
        pending.extend(chunk)
        while b'\n' in pending:
            line, _, rest = pending.partition(b'\n')
            pending = bytearray(rest)
            match = pattern.fullmatch(bytes(line) + b'\n')
            if match:
                values = [round(float(v) * 1000) for v in match[1].split(b',')]
                samples.append([round(time.monotonic() - start, 3), *values])
        if len(pending) > 8192:
            pending.clear()
        elapsed = time.monotonic() - start
        if elapsed - last_report >= 5:
            print(json.dumps({'seconds': round(elapsed, 1), 'frames': len(samples), 'last_mV_AIN0_to_9': samples[-1][1:] if samples else None}), flush=True)
            last_report = elapsed
finally:
    port.close()
    (out / 'raw.bin').write_bytes(raw)
    with (out / 'samples.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['elapsed_seconds', *[f'AIN{i}_mV' for i in range(10)]])
        w.writerows(samples)
channels = []
for i in range(10):
    v = [s[i+1] for s in samples]
    if v:
        channels.append({'channel': f'AIN{i}', 'min_mV': min(v), 'max_mV': max(v), 'span_mV': max(v)-min(v), 'median_mV': statistics.median(v), 'reaches_default_pickup_3250mV': max(v) >= 3250})
result = {'port': ports[0].device, 'baud': 460800, 'frames': len(samples), 'bytes': len(raw), 'elapsed_seconds': round(time.monotonic()-start, 2), 'channels': channels, 'frames_over_3300mV': sum(any(v > 3300 for v in s[1:]) for s in samples), 'output': str(out)}
(out / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2), flush=True)
if not samples:
    raise SystemExit('No valid ten-channel ADC frames captured; see raw.bin')
