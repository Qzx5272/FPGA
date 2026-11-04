"""Check nonblocking synthesized-PCM capture across two unrelated clocks."""
from pathlib import Path
import subprocess,os,json,hashlib,datetime
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/audio_visual';o=b/'evidence/pcm_snapshot';o.mkdir(exist_ok=True)
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[s/'pcm_snapshot.v',s/'tb_pcm_snapshot.v'];hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
c=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb_pcm_snapshot','-o',str(o/'test.vvp'),*map(str,files)],env=env,capture_output=True,text=True)
p=None
if c.returncode==0:p=subprocess.run([str(binary/'vvp.exe'),str(o/'test.vvp')],env=env,capture_output=True,text=True,timeout=30)
record=dict(status='passed' if p is not None and p.returncode==0 and 'PASS' in p.stdout else 'failed',
 scope='RTL unit simulation only:PCM snapshot RAM and bundled-data toggle handshake. No display,FFT,integrated timing or physical CDC/MTBF acceptance',updated=datetime.datetime.now().isoformat(),sources=hashes,compile_log=c.stdout+c.stderr,log=p.stdout+p.stderr if p else '')
(o/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
raise SystemExit(0 if record['status']=='passed' else 1)
