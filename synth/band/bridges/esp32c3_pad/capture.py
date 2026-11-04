"""Capture diagnostic USB output without toggling reset/boot control lines."""
import argparse
import time
from pathlib import Path
import serial

p = argparse.ArgumentParser()
p.add_argument('--port', default='COM8')
p.add_argument('--seconds', type=float, default=30)
p.add_argument('--output', required=True)
args = p.parse_args()
target = Path(args.output)
target.parent.mkdir(parents=True, exist_ok=True)
s = serial.Serial(port=None, baudrate=115200, timeout=0.25)
s.dtr = False
s.rts = False
s.port = args.port
s.open()
deadline = time.monotonic() + args.seconds
try:
    with target.open('ab', buffering=0) as log:
        while time.monotonic() < deadline:
            line = s.readline()
            if line:
                log.write(line)
                print(line.decode('utf-8', errors='replace').rstrip(), flush=True)
finally:
    s.close()
