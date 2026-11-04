"""Elaborate the experimental wrapper; not a behavioral or physical test."""
from pathlib import Path
import os,subprocess,json,hashlib
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--microphone',action='store_true');a=ap.parse_args()
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder'
o=b/'evidence'/('microphone_top' if a.microphone else 'singer_board_engine');o.mkdir(exist_ok=True)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+list((s/'integration').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/audio_pt8211_queue.v']+[r/'synth/rtl'/n for n in ('hq_sine_quarter.v','uart.v','audio_serial.v')]
files+=list((b/'experimental/audio_input').glob('*.v'))
p=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','band_microphone_top' if a.microphone else 'band_singer_board_engine','-o',str(o/'engine.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True,timeout=30)
d=dict(status='passed_elaboration_only' if not p.returncode else 'failed',log=p.stdout+p.stderr,sha256={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log']);raise SystemExit(p.returncode)
