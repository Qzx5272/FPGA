"""Decode candidate I2S queue, including WS lead, FIFO ordering and panic."""
from pathlib import Path
import os,subprocess,json,hashlib
root=Path(__file__).resolve().parents[3];out=Path('D:/StarclusterBuilds/pcm5102_song_audio_20261031')
source=root/'synth/band/experimental/vocoder/tb_audio_pt8211_queue.v'
s=source.read_text().replace('tb_audio_pt8211_queue','tb_pcm5102_song')
s=s.replace('if(bits==16&&ws!==0)$fatal(1,"Right slot WS");','if(ws !== ((bits>=16 && bits<=31)?1\'b1:1\'b0)) $fatal(1,"I2S WS one-bit lead at bit %0d",bits);')
s=s.replace('if(ws!==1)$fatal(1,"Left slot WS");','if(ws!==0)$fatal(1,"Next left WS lead");')
s=s.replace('{er,el}','{el,er}').replace('PASS PT8211:','PASS PCM5102 standard I2S:')
tb=out/'tb_pcm5102_song.v';tb.write_text(s)
bin=root/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(bin)+os.pathsep+str(bin.parent/'lib')+os.pathsep+env['PATH']
files=[out/'audio_serial.v',out/'audio_pt8211_queue.v',tb]
c=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-s','tb_pcm5102_song','-o',str(out/'serial.vvp'),*map(str,files)],env=env,capture_output=True,text=True)
assert c.returncode==0,c.stderr
p=subprocess.run([str(bin/'vvp.exe'),str(out/'serial.vvp')],env=env,capture_output=True,text=True,timeout=30)
r=dict(status='passed' if p.returncode==0 else 'failed',log=p.stdout+p.stderr,sources={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(out/'serial_test.json').write_text(json.dumps(r,indent=2));print(r['log']);assert p.returncode==0
