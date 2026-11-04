"""Real band ownership/dispatch -> dedicated singer event integration."""
from pathlib import Path
import subprocess,os,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder';o=b/'evidence/singer_stress';o.mkdir(exist_ok=True)
tools=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/band_singer_core.sv',r/'synth/rtl/hq_sine_quarter.v',s/'tb_singer_stress.v']
tb=s/'tb_singer_stress.v'
# Relocate the generated test's coefficient parameter for fresh checkouts.
import re
text=re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("'+(s/'ported/coeffs.mem').as_posix()+'")',tb.read_text())
(o/'tb.v').write_text(text)
compile_files=[p for p in files if p!=tb]+[o/'tb.v']
c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','tb_singer_stress','-o',str(o/'test.vvp')]+[str(p) for p in compile_files],env=env,capture_output=True,text=True)
(o/'compile.log').write_text(c.stderr)
if c.returncode:raise RuntimeError(c.stderr)
(o/'result.json').write_text(json.dumps(dict(status='running',scope='256voice+singer RTL load transition',prior_attempt='Simulator killed by60second host timeout; no pass/fail conclusion on design')) )
p=subprocess.run([str(tools/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=300)
d=dict(status='passed' if not p.returncode else 'failed',scope='256bandvoices+singer,1024loaded+16releaseframes simulation; not long-term or board timing acceptance',log=p.stdout+p.stderr,sha256={str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in files})
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log'])
if p.returncode:raise SystemExit(1)
