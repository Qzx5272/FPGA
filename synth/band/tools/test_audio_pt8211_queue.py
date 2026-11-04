"""Decode actual DAC serial output, including empty-latch enqueue race."""
from pathlib import Path
import os,subprocess,json,hashlib
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--jitter',action='store_true');a=ap.parse_args()
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder'
name='audio_pt8211_jitter' if a.jitter else 'audio_pt8211_queue'
o=b/'evidence'/name;o.mkdir(exist_ok=True)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=[s/'integration/audio_pt8211_queue.v',r/'synth/rtl/audio_serial.v',s/('tb_'+name+'.v')]
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-s','tb_'+name,'-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=30)
d=dict(status='passed' if p.returncode==0 else 'failed',scope='RTL serial decoding, not physical DAC acceptance',log=p.stdout+p.stderr,sha256={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['log'])
raise SystemExit(p.returncode)
