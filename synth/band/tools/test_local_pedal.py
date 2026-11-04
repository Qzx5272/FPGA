from pathlib import Path
import os,subprocess,json,hashlib,sys
r=Path(__file__).resolve().parents[3];b=r/'synth/band';folder=b/'experimental/local_pedal'
subprocess.run([sys.executable,str(b/'tools/prepare_local_pedal.py')],check=True)
sources=[b/'rtl/local_performer.v',b/'rtl/track_ownership.v',*folder.glob('*.v')]
o=b/'evidence/local_pedal';o.mkdir(exist_ok=True)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb_local_pedal','-o',str(o/'test.vvp'),*map(str,sources)],env=env,capture_output=True,text=True)
(o/'compile.log').write_text(c.stdout+c.stderr)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(binary/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=60)
record=dict(status='passed' if not p.returncode else 'failed',scope='Local performer wrapper and real ownership RTL; no physical pins/full band timing claim',sources={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},log=p.stdout+p.stderr)
(o/'result.json').write_text(json.dumps(record,indent=2));print(record['log']);raise SystemExit(p.returncode)
