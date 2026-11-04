"""Simulation-only idle skipping; accept ONLY after full-clock PCM equivalence.
The board RTL/export and existing 96-second golden evidence are never changed.
"""
from pathlib import Path
import os,sys,subprocess,hashlib,json,shutil,time,wave,re
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
seconds=float(sys.argv[1]) if len(sys.argv)>1 else 100
export=r/'output/final_workstation_20261022/offline_singer_confluence'
driver=b/'tests/singer_render.cpp'
inputs=sorted((export/'rtl').glob('*'))+[export/'coeffs.mem',driver]
original={p.name:p.read_bytes() for p in inputs if p.is_file()}
content=dict(original)
base=(b/'rtl/band_core.v').read_text()
idle=re.search(r'assign simulation_idle=(.*?);',base).group(1).replace('audio_valid','band_audio_valid')
idle+='&&!audio_valid&&electronic_singer.carrier_ready&&!electronic_singer.carrier_valid&&!electronic_singer.band_pending&&!electronic_singer.carrier_pending&&electronic_singer.insert_ready&&!electronic_singer.notes.scanning&&electronic_singer.notes.allocator_ready&&!electronic_singer.notes.done'
core=content['band_singer_core.sv'].decode()
assert core.count("assign simulation_idle=1'b0;")==1
content['band_singer_core.sv']=core.replace("assign simulation_idle=1'b0;",'assign simulation_idle='+idle+';').encode()
cpp=content[driver.name].decode()
old='for(unsigned c=1;c<(n%3==0?1041u:1042u);c++)tick();'
assert cpp.count(old)==1
cpp=cpp.replace(old,'''for(unsigned c=1;c<(n%3==0?1041u:1042u);c++){
   tick();
   if(d.simulation_idle){unsigned skipped=(n%3==0?1041u:1042u)-c-1;clocks+=skipped;context.timeInc(2*skipped);break;}
  }''')
content[driver.name]=cpp.encode()
hashes={name:hashlib.sha256(data).hexdigest() for name,data in content.items()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('singer_tail_'+digest);build.mkdir(exist_ok=True)
snap=build/'source_snapshot';snap.mkdir(exist_ok=True)
for name,data in content.items():
 p=snap/name
 if p.exists():assert p.read_bytes()==data
 else:p.write_bytes(data)
binary=r/'tmp/oss-cad-suite/bin';vr=r/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
exe=build/'render.exe'
def run_logged(cmd,name):
 with (build/name).open('w') as log:p=subprocess.run(cmd,env=env,cwd=snap,stdout=log,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError(str(build/name))
if not exe.exists():
 run_logged([str(binary/'verilator_bin.exe'),'--cc','--top-module','band_singer_core','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*map(str,sorted(snap.glob('*.v'))+sorted(snap.glob('*.sv')))],'verilator.log')
 run_logged(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/driver.name),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
o=b/'evidence/singer_render';o.mkdir(exist_ok=True);name=f'{digest}_{seconds:g}s_tail';report=o/(name+'.json');pcm=o/(name+'.pcm')
if report.exists():raise RuntimeError('Inspect existing evidence; refusing overwrite '+str(report))
golden=o/('2f695e9c1f4f_0.05s.json' if seconds==0.05 else '2f695e9c1f4f_96s.json')
reference=json.loads(golden.read_text());assert reference['status']=='passed'
if seconds<reference['seconds']:raise ValueError('Render must cover the entire golden interval')
record=dict(status='running_unproven_idle_skip',scope='Simulation-only variant; must match complete golden PCM before acceptance. Synthetic microphone, no physical claim',seconds=seconds,source_hashes=hashes,original_source_hashes={name:hashlib.sha256(data).hexdigest() for name,data in original.items()},build=str(build),executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),golden=str(golden))
report.write_text(json.dumps(record,indent=2));start=time.monotonic();env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH']
with (o/(name+'.log')).open('w') as log:p=subprocess.run([str(exe),str(pcm),str(round(seconds*48000))],cwd=snap,env=env,stdout=log,stderr=subprocess.STDOUT)
record.update(status='failed',returncode=p.returncode,elapsed_seconds=time.monotonic()-start,log=(o/(name+'.log')).read_text())
if p.returncode==0 and pcm.stat().st_size==round(seconds*48000)*4:
 with pcm.open('rb') as f:prefix=f.read(round(reference['seconds']*48000)*4)
 record['full_clock_prefix_identical']=hashlib.sha256(prefix).hexdigest()==reference['pcm_sha256']
 if record['full_clock_prefix_identical']:
  wav=o/(name+'.wav')
  with wave.open(str(wav),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.read_bytes())
  record.update(status='passed',wav=str(wav),pcm_sha256=hashlib.sha256(pcm.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if 'source_hashes' not in k},indent=2),flush=True)
raise SystemExit(0 if record['status']=='passed' else 1)
