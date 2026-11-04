"""Compile the actual RTL to C++ for long, cycle-accurate spectral tests."""
from pathlib import Path
import subprocess,os,sys,json,hashlib,time,shutil
root=Path(__file__).resolve().parents[3];os.chdir(root)
band=root/'synth/band';lb=int(sys.argv[1]) if len(sys.argv)>1 else 3;ab=int(sys.argv[2]) if len(sys.argv)>2 else 9;lanes=int(sys.argv[3]) if len(sys.argv)>3 else 1<<lb;n=lanes<<ab
if lb not in (3,4,5,6) or ab not in (9,10) or not 0<lanes<=1<<lb or n>=65536:raise ValueError('Invalid diagnostic dimensions')
diverse=len(sys.argv)>4 and sys.argv[4]=='diverse';suffix='_diverse' if diverse else ''
build=band/f'build/verilated_pool{n}{suffix}';build.mkdir(parents=True,exist_ok=True)
evidence=band/'evidence';binary=root/'tmp/oss-cad-suite/bin';vr=root/'tmp/oss-cad-suite/share/verilator'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
sources=[band/'rtl/partial_pool.v',band/'rtl/partial_lane.v',band/'rtl/partial_ram16.v',root/'synth/rtl/hq_sine_quarter.v']
snap=build/'source_snapshot';snap.mkdir(exist_ok=True)
for p in sources+[root/'synth/rtl/sine_quarter_init.vh',band/'tests/pool_driver.cpp']:shutil.copy2(p,snap/p.name)
cmd=[str(binary/'verilator_bin.exe'),'--cc','--top-module','partial_pool','--Mdir',str(build),'-Wno-fatal',f'-GLANE_BITS={lb}',f'-GADDRESS_BITS={ab}',f'-GLANES={lanes}','-I'+str(root/'synth/rtl'),*[str(p) for p in sources]]
c=subprocess.run(cmd,env=env,capture_output=True,text=True);(build/'verilator.log').write_text(c.stdout+c.stderr)
if c.returncode:raise RuntimeError(c.stdout+c.stderr)
exe=build/'measure.exe'
cmd=['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(band/'tests/pool_driver.cpp'),*[str(p) for p in build.glob('*.cpp')],str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)]
c=subprocess.run(cmd,env=env,capture_output=True,text=True);(build/'compile.log').write_text(c.stdout+c.stderr)
if c.returncode:raise RuntimeError(c.stdout+c.stderr)
record={'profile':'cycle-accurate Verilator RTL simulation; not board measurement','partials':n,'state':'running','sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snap.iterdir()},'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
report=evidence/f'pool{n}{suffix}_verilated.json';report.write_text(json.dumps(record,indent=2))
samples=evidence/f'pool{n}{suffix}_verilated_samples.txt';t=time.monotonic()
run_env=dict(env)
# Use the compiler's matching runtime, not OSS-CAD's different libstdc++ DLL.
compiler_dir=str(Path(shutil.which('g++')).parent)
run_env['PATH']=compiler_dir+os.pathsep+env['PATH']
r=subprocess.run([str(exe),str(samples),str(n),'135168']+(['diverse'] if diverse else []),env=run_env,capture_output=True,text=True,timeout=14400)
record.update(elapsed_seconds=time.monotonic()-t,log=r.stdout+r.stderr,returncode=r.returncode)
if r.returncode:record['state']='failed';report.write_text(json.dumps(record,indent=2));raise RuntimeError(record)
import numpy as np
x=np.loadtxt(samples,dtype=np.float64)[-131072:];spectrum=np.abs(np.fft.rfft(x))*2/len(x)
spacing=1 if n>16384 else 3 if n>8192 else 5
bins=50+spacing*np.arange(n);amp=spectrum[bins]
targets=45000+(np.arange(n)*37)%15000 if diverse else 60000
expected=131071*(targets/65536)*64/(1<<(lb+ab));error=np.abs(amp-expected)/expected
record['normalization_divisor']=1<<(lb+ab)
record['fft_bin_spacing']=spacing
record.update(state='passed' if np.all(error<.03) else 'failed',diverse_envelopes=diverse,verified_peaks=int(np.count_nonzero(error<.03)),minimum_peak=float(amp.min()),maximum_peak=float(amp.max()),expected_peak_range=[float(np.min(expected)),float(np.max(expected))],max_relative_error=float(error.max()),sample_peak=float(np.max(np.abs(x))),sample_sha256=hashlib.sha256(samples.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)
if record['state']!='passed':raise RuntimeError('Spectrum mismatch')
