"""Full-clock immutable combined export render; no microphone, actual band-driven display consumer."""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,time,re
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
frames=int(sys.argv[1]) if len(sys.argv)>1 else 9600
if frames<1024:raise ValueError('At least1024 loaded frames required')
export=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else r/'output/final_workstation_20261022/offline_workstation_video_confluence'
load_fixture='--load' in sys.argv[3:]
load_release=int(sys.argv[sys.argv.index('--load-release')+1]) if '--load-release' in sys.argv[3:] else 5000
if load_fixture and (load_release<=500 or frames<load_release+2000):raise ValueError('Load needs settling, release and final tail frames')
if not load_fixture and '--load-release' in sys.argv[3:]:raise ValueError('--load-release requires --load')
sys.path.insert(0,str(b/'host'))
from rom_contract import check_vocoder_rom
check_vocoder_rom(export/'rtl/filterbank.sv')
driver=b/'tests/workstation_video_probe.cpp'
inputs=sorted((export/'rtl').glob('*'))+list(export.glob('*.mem'))+[driver,b/'tests/workstation_video_probe.sv',Path(__file__)]
manifest=json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['sources'].items():
 assert hashlib.sha256((export/name).read_bytes()).hexdigest()==h,name
data={p.name:p.read_bytes() for p in inputs if p.is_file()}
hashes={n:hashlib.sha256(v).hexdigest() for n,v in data.items()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('workstation_video_probe_'+digest);build.mkdir(exist_ok=True)
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
 # All hardware clocks are driven by C++; ignore the simulation-only startup
 # delay in the coefficient check. The same range is checked above before build.
 run([str(binary/'verilator_bin.exe'),'--cc','--no-timing','--top-module','workstation_video_probe','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*map(str,sorted(snap.glob('*.v'))+sorted(snap.glob('*.sv')))],'verilator.log')
 run(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/driver.name),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
o=b/'evidence/workstation_video_probe';o.mkdir(exist_ok=True);name=f'{digest}_{frames}frames';report=o/(name+'.json');pcm=o/(name+'.pcm')
if report.exists():raise RuntimeError('Refusing to overwrite evidence '+str(report))
record=dict(status='running',scope='Full-clock combined exported top: exact 50MHz/24.576MHz/25.2MHz clocks, autonomous score, I2S queue and active logical RGB raster; microphone absent, no physical or serial-pin equality claim',load_fixture=load_fixture,load_release_frame=load_release if load_fixture else None,loaded_frames=frames,loaded_seconds=frames/48000,source_hashes=hashes,build=str(build),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2));env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH'];start=time.monotonic()
with (o/(name+'.log')).open('w') as log:p=subprocess.run([str(exe),str(pcm),str(frames)]+(['--load',str(load_release)] if load_fixture else []),cwd=snap,env=env,stdout=log,stderr=subprocess.STDOUT)
record.update(status='passed' if p.returncode==0 and pcm.stat().st_size==frames*4 else 'failed',returncode=p.returncode,elapsed_seconds=time.monotonic()-start,log=(o/(name+'.log')).read_text())
metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',record['log'])}
record['aggregate_output_nonzero']=metrics.get('peak',0)>0
if not record['aggregate_output_nonzero']:record['status']='failed'
record['export_build_id']=manifest['build_id']
record['pcm_sha256']=hashlib.sha256(pcm.read_bytes()).hexdigest()
report.write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2))
sys.exit(0 if record['status']=='passed' else 1)
