"""Universal shared bank versus original renderer, role-aware stereo and full choir load."""
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
out = band / 'evidence/shared_voice_bank' / stamp
out.mkdir(parents=True)
cad = root / 'tmp/oss-cad-suite'
env = dict(os.environ)
env['PATH'] = str(cad/'bin') + os.pathsep + str(cad/'lib') + os.pathsep + env['PATH']
files = [source/n for n in ('shared_note_allocator.v','shared_voice_bank.v','shared_band_renderer.v','tb_shared_voice_bank.sv')]
files += [band/'rtl'/n for n in ('voice_bank.v','note_allocator.v','band_renderer.v')] + [root/'synth/rtl/hq_sine_quarter.v']
compiled = subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-I',str(band/'rtl'),'-I',str(root/'synth/rtl'),'-s','tb','-o',str(out/'test.vvp'),*[str(p) for p in files]],env=env,capture_output=True,text=True,timeout=30)
simulation = None
if compiled.returncode == 0:
    simulation = subprocess.run([str(cad/'bin/vvp.exe'),str(out/'test.vvp')],env=env,capture_output=True,text=True,timeout=30)
passed = compiled.returncode == 0 and simulation is not None and simulation.returncode == 0 and 'PASS universal bank' in simulation.stdout
record = dict(status='passed' if passed else 'failed',created=datetime.datetime.now().isoformat(),
    scope='Single universal bank: eight roles64samples each match original single-note PCM with role-aware stereo; other-role expression isolation; lead identity;32choir64samples at1042clocks/sample. Not full256-voice audio, synthesis, timing or board acceptance.',
    production_adopted=False,
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[Path(__file__)]+list((band/'rtl').glob('*.vh'))+[root/'synth/rtl/sine_quarter_init.vh']},
    compile_output=compiled.stdout+compiled.stderr,
    simulation_output=simulation.stdout+simulation.stderr if simulation else 'not run')
(out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record,indent=2))
if not passed:
    raise SystemExit(1)
