"""Verify dedicated audio image; --program loads SRAM only. Never touches Flash."""
from pathlib import Path
import argparse,hashlib,json,subprocess,re,datetime
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--program',action='store_true')
ap.add_argument('--location',type=int,default=0);ap.add_argument('--channel',type=int,default=0)
args=ap.parse_args();root=Path(__file__).resolve().parents[3]
release=root/'output/i2s_audio_20261031'
manifest=json.loads((release/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert manifest['status']=='digital_build_verified_physical_test_pending'
assert all(manifest[k+'_violations']==0 for k in ('setup','hold','pulse_width'))
for n,h in manifest['sources'].items():assert sha(release/n)==h,n
bit=release/'i2s_duplex.fs';assert sha(bit)==manifest['bitstream_sha256']
assert json.loads((release/'simulation.json').read_text())['status']=='passed'
if not args.program:
 print('PASS preflight; no USB accessed. Dedicated tone/mic test image, not workstation.');raise SystemExit(0)
programmer=Path('D:/Gowin/Gowin_V1.9.12.03_x64/Programmer/bin/programmer_cli.exe')
assert programmer.is_file()
out=root/'synth/band/evidence'/('i2s_sram_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
out.mkdir()
def run(arguments,name,timeout):
 p=subprocess.run([str(programmer),*arguments],capture_output=True,text=True,errors='replace',timeout=timeout)
 text=p.stdout+p.stderr;(out/(name+'.log')).write_text(text,encoding='utf-8')
 if p.returncode or re.search(r'\b(error|failed|failure)\b',text,re.I):raise RuntimeError(text)
 return text
assert 'Cable found:' in run(['--scan-cables','F'],'scan',15)
base=['--device','GW5AST-138B','--cable-index','4','--location',str(args.location),'--channel',str(args.channel)]
probe=run([*base,'--run','0'],'probe',15)
assert re.search(r'success|IDCODE|ID code',probe,re.I)
text=run([*base,'--run','2','--fsFile',str(bit)],'sram',90)
assert re.search(r'success',text,re.I) or ('100%' in text and 'Finished.' in text)
(out/'loaded_manifest.json').write_text(json.dumps(manifest,indent=2))
print('SRAM loaded; Flash unchanged. Press S0 for tone, S1 for microphone, S2 to mute. Analog test pending.')
