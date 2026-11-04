"""Freeze the actual exported full-top and test video/audio clock loss together."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,time
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
export=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else r/'output/final_workstation_20261022/offline_workstation_video_confluence'
manifest=json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
assert manifest['hardware_profile']=='workstation-i2s-rgb-v1'
for name,h in manifest['sources'].items():assert hashlib.sha256((export/name).read_bytes()).hexdigest()==h,name
inputs=sorted((export/'rtl').glob('*'))+list(export.glob('*.mem'))+[b/'tests/workstation_video_probe.sv',b/'tests/workstation_video_faults.cpp',Path(__file__)]
data={p.name:p.read_bytes() for p in inputs if p.is_file()};hashes={n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('workstation_video_faults_'+digest);build.mkdir(exist_ok=False)
snap=build/'source_snapshot';snap.mkdir()
for name,content in data.items():(snap/name).write_bytes(content)
binary=r/'tmp/oss-cad-suite/bin';vr=r/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
def run(cmd,name):
 with (build/name).open('w') as log:p=subprocess.run(cmd,env=env,cwd=snap,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/name))
out=b/'evidence/workstation_video_faults'/digest;out.mkdir(parents=True)
record=dict(status='running',build=str(build),source_hashes=hashes,scope='Actual full exported band:140ms exact clocks,20ms video stall,3ms audio loss while video stopped,asynchronous stale-frame clear,qualified recovery without automatic replay. No physical/HDMI/panic-button claim.')
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(build,flush=True)
try:
 run([str(binary/'verilator_bin.exe'),'--cc','--no-timing','--top-module','workstation_video_probe','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*map(str,sorted(snap.glob('*.v'))+sorted(snap.glob('*.sv')))],'verilator.log')
 exe=build/'faults.exe'
 run(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/'workstation_video_faults.cpp'),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
 start=time.monotonic();run([str(exe)],'run.log');record.update(status='passed',elapsed_seconds=time.monotonic()-start,log=(build/'run.log').read_text(),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
except Exception as e:record.update(status='failed',error=str(e));raise
finally:
 for p in build.glob('*.log'):(out/p.name).write_bytes(p.read_bytes())
 report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2))
