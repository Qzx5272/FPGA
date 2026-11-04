"""Two-phase shared allocation with real per-bank allocators, no sound renderer."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

band = Path(__file__).resolve().parents[1]
root = band.parents[1]
source = band / 'experimental/shared_voices'
stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out = band / 'evidence/shared_bank_dispatch' / stamp
out.mkdir(parents=True)
cad = root / 'tmp/oss-cad-suite'
env = dict(os.environ)
env['PATH'] = str(cad/'bin') + os.pathsep + str(cad/'lib') + os.pathsep + env['PATH']
files = [source/n for n in ('shared_bank_dispatch.v','shared_note_allocator.v','tb_shared_bank_dispatch.sv')]
compiled = subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),*[str(p) for p in files]],env=env,capture_output=True,text=True,timeout=30)
simulation = None
if compiled.returncode == 0:
    simulation = subprocess.run([str(cad/'bin/vvp.exe'),str(out/'test.vvp')],env=env,capture_output=True,text=True,timeout=30)
passed = compiled.returncode == 0 and simulation is not None and simulation.returncode == 0 and 'PASS shared256' in simulation.stdout
record = dict(status='passed' if passed else 'failed',created=datetime.datetime.now().isoformat(),
    scope='RTL allocator only:256 same-role identities across8banks, duplicate/full/tail/identity safety, delayed bank completion, blocked probe and panic. No synthesis, integrated musical controls, audio deadlines, physical capacity or adoption claim.',
    production_adopted=False,
    sources={str(p.relative_to(band)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]},
    compile_output=compiled.stdout+compiled.stderr,
    simulation_output=simulation.stdout+simulation.stderr if simulation else 'not run')
(out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
if not passed:
    raise SystemExit(1)
