"""Full-clock sustained256-band-voice+singer test; no audio-idle skipping."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,time,re
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
frames=int(sys.argv[1]) if len(sys.argv)>1 else 2880000
if frames<1024:raise ValueError('At least1024 loaded frames required')
export=r/'output/final_workstation_20261022/offline_singer_confluence'
driver=b/'tests/singer_sustained.cpp'
inputs=sorted((export/'rtl').glob('*'))+[export/'coeffs.mem',driver]
data={p.name:p.read_bytes() for p in inputs if p.is_file()}
hashes={n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('singer_sustained_'+digest);build.mkdir(exist_ok=True)
snap=build/'source_snapshot';snap.mkdir(exist_ok=True)
for name,content in data.items():
 p=snap/name
 if p.exists():assert p.read_bytes()==content
 else:p.write_bytes(content)
binary=r/'tmp/oss-cad-suite/bin';vr=r/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
exe=build/'stress.exe'
def run(cmd,name):
 with (build/name).open('w') as log:p=subprocess.run(cmd,env=env,cwd=snap,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/name))
if not exe.exists():
 run([str(binary/'verilator_bin.exe'),'--cc','--top-module','band_singer_core','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*map(str,sorted(snap.glob('*.v'))+sorted(snap.glob('*.sv')))],'verilator.log')
 run(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/driver.name),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
o=b/'evidence/singer_sustained';o.mkdir(exist_ok=True);name=f'{digest}_{frames}frames';report=o/(name+'.json');pcm=o/(name+'.pcm')
if report.exists():raise RuntimeError('Refusing to overwrite evidence '+str(report))
record=dict(status='running',scope='Full-clock exported singer core:256held band slots plus singer,delay,synthetic microphone; no board or individual audibility claim',loaded_frames=frames,loaded_seconds=frames/48000,source_hashes=hashes,build=str(build),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2));env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH'];start=time.monotonic()
with (o/(name+'.log')).open('w') as log:p=subprocess.run([str(exe),str(pcm),str(frames)],cwd=snap,env=env,stdout=log,stderr=subprocess.STDOUT)
record.update(status='passed' if p.returncode==0 and pcm.stat().st_size==(frames+32)*4 else 'failed',returncode=p.returncode,elapsed_seconds=time.monotonic()-start,log=(o/(name+'.log')).read_text())
metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',record['log'])}
record['aggregate_output_nonzero']=metrics.get('peak',0)>0 and metrics.get('nonzero_frames',0)>=frames//2
if not record['aggregate_output_nonzero']:record['status']='failed'
record['pcm_sha256']=hashlib.sha256(pcm.read_bytes()).hexdigest()
report.write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2))
sys.exit(0 if record['status']=='passed' else 1)
