"""Adversarial variable band-render completion, baseline mutation retained."""
from pathlib import Path
import os,json,subprocess,hashlib
R=Path(__file__).resolve().parents[3];B=R/'synth/band';S=B/'experimental/vocoder';O=B/'evidence/singer_schedule';O.mkdir(exist_ok=True)
tb=(S/'tb_singer_schedule.sv').read_text().replace('COEFF_PATH',(S/'ported/coeffs.mem').as_posix());(O/'tb.sv').write_text(tb)
sources=[S/'ported'/n for n in ('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv','band_vocoder_insert.sv','vocoder_carrier.sv','vocoder_band_lane.sv','singer_note_control.v')]+[B/'rtl/note_allocator.v',R/'synth/rtl/hq_sine_quarter.v']
tools=R/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
result={}
for variant,module in [('serial',O/'serial_singer_role.sv'),('current',S/'ported/singer_role.sv')]:
 c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-I',str(S/'ported'),'-I',str(B/'rtl'),'-I',str(R/'synth/rtl'),'-s','tb','-o',str(O/(variant+'.vvp'))]+[str(p) for p in sources]+[str(module),str(O/'tb.sv')],env=env,capture_output=True,text=True)
 if c.returncode:raise RuntimeError(c.stderr)
 r=subprocess.run([str(tools/'vvp.exe'),str(O/(variant+'.vvp'))],env=env,cwd=O,capture_output=True,text=True,timeout=30)
 result[variant]=dict(returncode=r.returncode,log=r.stdout+r.stderr,source_sha256=hashlib.sha256(module.read_bytes()).hexdigest())
record=dict(status='passed' if result['serial']['returncode']!=0 and result['current']['returncode']==0 else 'failed',scope='Variable completion schedule only; serial baseline must demonstrate drop',variants=result)
(O/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
if record['status']!='passed':raise SystemExit(1)
