"""Full-clock exported singer RTL rendering. No quiescent-clock skipping."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,time,wave
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
seconds=float(sys.argv[1]) if len(sys.argv)>1 else 96
export=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else r/'output/final_workstation_20261022/offline_singer_confluence'
manifest=json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
for name,digest in manifest['sources'].items():
 assert hashlib.sha256((export/name).read_bytes()).hexdigest()==digest,name
sys.path.insert(0,str(b/'host'))
from rom_contract import check_vocoder_rom
from singer_render_contract import check_render_score
score_contract=check_render_score(json.loads((export/'project.json').read_text(encoding='utf-8')),seconds)
check_vocoder_rom(export/'rtl/filterbank.sv')
driver=b/'tests/singer_render.cpp'
inputs=sorted((export/'rtl').glob('*'))+list(export.glob('*.mem'))+[export/'project.json',b/'host/singer_render_contract.py',driver,Path(__file__)]
hashes={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs if p.is_file()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('singer_render_'+digest);build.mkdir(exist_ok=True)
snap=build/'source_snapshot';snap.mkdir(exist_ok=True)
for p in inputs:
 if p.is_file():shutil.copy2(p,snap/p.name)
binary=r/'tmp/oss-cad-suite/bin';vr=r/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
exe=build/'render.exe'
def run_logged(cmd,name):
 with (build/name).open('w') as log:
  p=subprocess.run(cmd,env=env,cwd=snap,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/name))
if not exe.exists():
 sources=sorted(snap.glob('*.v'))+sorted(snap.glob('*.sv'))
 # Clock edges are driven explicitly by C++; ROM shape is checked above.
 # Only the simulation-only ROM startup delay is ignored, as in workstation rendering.
 run_logged([str(binary/'verilator_bin.exe'),'--cc','--no-timing','--top-module','band_singer_core','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*map(str,sources)],'verilator.log')
 run_logged(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/driver.name),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
o=b/'evidence/singer_render';o.mkdir(exist_ok=True)
name=f'{digest}_{seconds:g}s';report=o/(name+'.json');pcm=o/(name+'.pcm')
if report.exists():raise RuntimeError('Preserve existing render evidence: '+str(report))
record=dict(status='running',scope='Exported band_singer_core full-clock RTL only; synthetic microphone; driver overrides master64/wet24/tempo120/singer_mix127; not full board top, physical audio or saved mixer preset acceptance',export=str(export),export_build_id=manifest.get('build_id'),seconds=seconds,source_hashes=hashes,build=str(build),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
record['score_contract']=score_contract
report.write_text(json.dumps(record,indent=2));start=time.monotonic()
env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH']
with (o/(name+'.log')).open('w') as log:
 p=subprocess.run([str(exe),str(pcm),str(round(seconds*48000))],cwd=snap,env=env,stdout=log,stderr=subprocess.STDOUT)
record.update(status='passed' if p.returncode==0 and pcm.stat().st_size==round(seconds*48000)*4 else 'failed',returncode=p.returncode,elapsed_seconds=time.monotonic()-start,log=(o/(name+'.log')).read_text())
if record['status']=='passed':
 wav=o/(name+'.wav')
 with wave.open(str(wav),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.read_bytes())
 record.update(wav=str(wav),pcm_sha256=hashlib.sha256(pcm.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2),flush=True)
raise SystemExit(0 if record['status']=='passed' else 1)
