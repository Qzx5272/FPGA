"""Actual RTL audition. Optional proven-quiescent clock skipping, no CPU audio model."""
from pathlib import Path
import subprocess,os,sys,json,hashlib,time,shutil,wave
root=Path(__file__).resolve().parents[3];os.chdir(root);band=root/'synth/band'
seconds=float(sys.argv[1]) if len(sys.argv)>1 else 97
mode=sys.argv[2] if len(sys.argv)>2 else 'fast'
if mode not in ('fast','full','stress','audition','audition_fast','matrix'):raise ValueError('Expected fast, full, stress, audition, audition_fast or matrix')
sources=[band/'rtl'/n for n in ('band_core.v','voice_bank.v','band_renderer.v','note_allocator.v','track_ownership.v','song_sequencer.v','song_store.v','stereo_delay.v')]+[root/'synth/rtl/hq_sine_quarter.v']
dependencies=sources+list((band/'rtl').glob('*.vh'))+[root/'synth/rtl/sine_quarter_init.vh',band/'tests/band_driver.cpp']
digest=hashlib.sha256(b''.join(p.read_bytes() for p in dependencies)).hexdigest()[:12]
build=band/f'build/verilated_band_{digest}';build.mkdir(parents=True,exist_ok=True);evidence=band/'evidence'
binary=root/'tmp/oss-cad-suite/bin';vr=root/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
snap=build/'source_snapshot';snap.mkdir(exist_ok=True)
for p in dependencies:shutil.copy2(p,snap/p.name)
exe=build/'render.exe'
def compile_model():
 if exe.exists():return
 cmd=[str(binary/'verilator_bin.exe'),'--cc','--top-module','band_core','--Mdir',str(build),'-Wno-fatal','-I'+str(snap),*[str(snap/p.name) for p in sources]]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True);(build/'verilator.log').write_text(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError(c.stdout+c.stderr)
 cmd=['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/'band_driver.cpp'),*[str(p) for p in build.glob('*.cpp')],str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)]
 c=subprocess.run(cmd,env=env,capture_output=True,text=True);(build/'compile.log').write_text(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError(c.stdout+c.stderr)
lock=build/'compile.lock';locked=False
try:
 for attempt in range(2400):
  try:
   fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd);locked=True;break
  except FileExistsError:time.sleep(.25)
 if not locked:raise RuntimeError('Compile lock timeout; check the recorded process before removing '+str(lock))
 compile_model()
finally:
 if locked:lock.unlink()
name=f'band_{digest}_{seconds:g}s_{mode}'
record={'status':'running','evidence_level':'RTL simulation only','mode':mode,'duration_seconds':seconds,'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()},'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
report=evidence/(name+'.json');report.write_text(json.dumps(record,indent=2))
run_env=dict(env);run_env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH']
pcm=evidence/(name+'.pcm');t=time.monotonic()
r=subprocess.run([str(exe),str(pcm),str(round(seconds*48000)),mode],env=run_env,capture_output=True,text=True,timeout=14400)
record.update(status='passed' if r.returncode==0 else 'failed',returncode=r.returncode,log=r.stdout+r.stderr,elapsed_seconds=time.monotonic()-t)
if r.returncode==0 and pcm.stat().st_size!=round(seconds*48000)*4:
 record.update(status='failed',returncode=98,log=record['log']+'FAIL incomplete PCM file; check storage capacity\n');r.returncode=98
if r.returncode==0:
 wav=evidence/(name+'.wav')
 with wave.open(str(wav),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.read_bytes())
 record['pcm_sha256']=hashlib.sha256(pcm.read_bytes()).hexdigest();record['wav']=str(wav)
 reference=evidence/f'band_{digest}_{seconds:g}s_full.json'
 if mode=='fast' and reference.exists():
  prior=json.loads(reference.read_text())
  if prior.get('status')=='passed' and prior.get('pcm_sha256'):
   record['matches_full_clock_simulation']=prior['pcm_sha256']==record['pcm_sha256']
   if not record['matches_full_clock_simulation']:record['status']='failed';r.returncode=99
 if seconds>=90 and mode in ('fast','full') and record['status']=='passed':
  shutil.copy2(wav,evidence/'band_latest.wav');(evidence/'latest_band_render.json').write_text(json.dumps(record,indent=2))
report.write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='source_hashes'},indent=2),flush=True)
if r.returncode:raise RuntimeError('Integrated simulation failed')
