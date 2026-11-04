"""Independent pin-level full-duplex regression, not an analog acceptance test."""
from pathlib import Path
import os, subprocess, hashlib, json, math
root=Path(__file__).resolve().parents[3]
src=root/'synth/band/experimental/i2s_duplex'
out=root/'synth/band/evidence/i2s_duplex_20261031'
out.mkdir(parents=True,exist_ok=True)
binary=root/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[src/n for n in ('i2s_master_duplex.sv','tb_i2s_master_duplex.sv','audio_bringup_top.sv','tb_audio_bringup.sv','tone_1k.mem')]
logs=[];passed=True
for test,rtl in [('duplex',[files[0],files[1]]),('board',[files[0],files[2],files[3]])]:
 for command in ([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(out/(test+'.vvp')),*map(str,rtl)],
                 [str(binary/'vvp.exe'),str(out/(test+'.vvp'))]):
  p=subprocess.run(command,cwd=src,env=env,capture_output=True,text=True,timeout=60)
  logs.append(p.stdout+p.stderr)
  if p.returncode:break
 passed=passed and p.returncode==0 and 'PASS' in logs[-1]
record={'status':'passed' if passed else 'failed','scope':'pin-level digital simulation only',
 'sources':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},'log':''.join(logs)}
(out/'simulation.json').write_text(json.dumps(record,indent=2))
print(record['log'])
raise SystemExit(0 if passed else 1)
