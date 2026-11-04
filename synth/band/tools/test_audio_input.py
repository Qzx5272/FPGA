"""Isolated optional input-interface regressions; production RTL is unchanged."""
from pathlib import Path
import os,subprocess,json,hashlib,datetime
root=Path(__file__).resolve().parents[3];b=root/'synth/band';source=b/'experimental/audio_input'
out=b/'evidence/audio_input';out.mkdir(parents=True,exist_ok=True)
sources=list(source.glob('*.v'))+[b/'rtl/audio_cdc_fifo.v']
tools=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
record=dict(status='running',started=datetime.datetime.now().isoformat(),scope='RTL simulation only; not physical microphone, vocoder, pin assignment, PnR, or board integration',sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},tests={})
path=out/'result.json';path.write_text(json.dumps(record,indent=2))
try:
 for top in ('tb_i2s24_rx','tb_input_bridge'):
  c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s',top,'-o',str(out/(top+'.vvp')),*map(str,sources)],env=env,capture_output=True,text=True,timeout=30)
  if c.returncode:raise RuntimeError(c.stderr)
  r=subprocess.run([str(tools/'vvp.exe'),str(out/(top+'.vvp'))],env=env,capture_output=True,text=True,timeout=30)
  record['tests'][top]=r.stdout+r.stderr
  if r.returncode or 'PASS' not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
 record['status']='passed'
except Exception as exc:record.update(status='failed',error=str(exc));raise
finally:path.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
