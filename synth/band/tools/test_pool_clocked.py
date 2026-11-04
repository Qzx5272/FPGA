"""Immutable full-clock diagnostic spectrum verification, including larger pools."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, time
import numpy as np

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('partials', type=int, choices=(4096,8192,16384,32768,37888,43008))
args=parser.parse_args()
band=Path(__file__).resolve().parents[1]; root=band.parents[1]
n=args.partials
lb,ab,lanes={4096:(3,9,8),8192:(4,9,16),16384:(5,9,32),32768:(5,10,32),37888:(6,10,37),43008:(6,10,42)}[n]
frequency_step=5 if n<=8192 else 3 if n<=16384 else 1
assert 50+frequency_step*(n-1)<65536, 'Frequency bins must remain below Nyquist'
sources=[band/'rtl'/name for name in ('partial_pool.v','partial_lane.v','partial_ram16.v')]
sources += [root/'synth/rtl'/name for name in ('hq_sine_quarter.v','sine_quarter_init.vh')]
sources += [band/'tests/pool_clocked_driver.cpp',Path(__file__)]
hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(dict(partials=n,sources=hashes),sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('pool_clocked_'+digest)
snap=build/'source_snapshot';snap.mkdir(parents=True,exist_ok=True)
report=band/'evidence'/('pool_clocked_'+digest+'.json')
if report.exists():raise ValueError('Preserve existing evidence: '+str(report))
for p in sources:
 q=snap/p.name
 if q.exists() and q.read_bytes()!=p.read_bytes():raise ValueError('Snapshot collision')
 q.write_bytes(p.read_bytes())
cad=root/'tmp/oss-cad-suite';vr=cad/'share/verilator'
env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH'];env['VERILATOR_ROOT']=str(vr)
def run(cmd,log):
 with (build/log).open('w') as f:
  result=subprocess.run(cmd,cwd=snap,env=env,stdout=f,stderr=subprocess.STDOUT)
 if result.returncode:raise RuntimeError(str(build/log))
record=dict(status='compiling',partials=n,lane_bits=lb,address_bits=ab,lanes=lanes,normalization_divisor=1<<(lb+ab),frequency_step_bins=frequency_step,source_sha256=hashes,build=str(build),scope='Full-clock diagnostic RTL only; not board timing, full-band capacity, analog audibility or live-control proof')
report.write_text(json.dumps(record,indent=2))
run([str(cad/'bin/verilator_bin.exe'),'--cc','--top-module','partial_pool','--Mdir',str(build),'-Wno-fatal',f'-GLANE_BITS={lb}',f'-GADDRESS_BITS={ab}',f'-GLANES={lanes}','-I'+str(snap),*map(str,snap.glob('*.v'))],'verilator.log')
exe=build/'measure.exe'
run(['g++','-std=c++17','-O3','-pthread','-I'+str(vr/'include'),'-I'+str(vr/'include/vltstd'),'-I'+str(build),str(snap/'pool_clocked_driver.cpp'),*map(str,build.glob('*.cpp')),str(vr/'include/verilated.cpp'),str(vr/'include/verilated_threads.cpp'),'-o',str(exe)],'compile.log')
env['PATH']=str(Path(shutil.which('g++')).parent)+os.pathsep+env['PATH']
record.update(status='running',executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());report.write_text(json.dumps(record,indent=2))
samples=report.with_suffix('.samples.txt');start=time.monotonic()
with (build/'run.log').open('w') as f:
 result=subprocess.run([str(exe),str(samples),str(n),'135168'],env=env,cwd=snap,stdout=f,stderr=subprocess.STDOUT)
record.update(status='failed',returncode=result.returncode,elapsed_seconds=time.monotonic()-start,log=(build/'run.log').read_text())
if result.returncode==0:
 x=np.loadtxt(samples);assert len(x)==135168
 x=x[-131072:];bins=50+frequency_step*np.arange(n)
 amplitude=abs(np.fft.rfft(x))[bins]*2/len(x)
 # partial_pool shifts by address width, including unused lane address space.
 expected=131071*((45000+(np.arange(n)*37)%15000)/65536)*64/(1<<(lb+ab))
 error=abs(amplitude-expected)/expected
 record.update(status='passed' if np.all(error<.03) else 'failed',verified_peaks=int(np.count_nonzero(error<.03)),maximum_relative_error=float(error.max()),sample_sha256=hashlib.sha256(samples.read_bytes()).hexdigest(),sample_peak=float(abs(x).max()))
report.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
raise SystemExit(0 if record['status']=='passed' else 1)
