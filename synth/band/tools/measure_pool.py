"""Long RTL spectral experiment, separate from short CI. Never a board claim."""
import os,subprocess,json,hashlib,time,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3];os.chdir(root)
band=root/'synth/band';out=band/'evidence';binary=root/'tmp/oss-cad-suite/bin'
lane_bits=int(sys.argv[1]) if len(sys.argv)>1 else 3
count=1<<(lane_bits+9)
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
sources=[band/'rtl/partial_lane.v',band/'rtl/partial_pool.v',band/'rtl/partial_ram16.v',root/'synth/rtl/hq_sine_quarter.v',band/'tests/tb_pool.v']
target=out/f'pool{count}_spectrum.vvp'
cmd=[str(binary/'iverilog.exe'),'-g2012','-I',str(root/'synth/rtl'),'-s','tb_pool','-P',f'tb_pool.LB={lane_bits}','-o',str(target),*[str(p) for p in sources]]
subprocess.run(cmd,env=env,check=True,capture_output=True,text=True)
record={'profile':'RTL simulation only, 112-bit independent state; not full-band configuration','partials':count,'frames':135168,'source_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'state':'running'}
report=out/f'pool{count}_spectrum.json';report.write_text(json.dumps(record,indent=2),encoding='utf-8')
t=time.monotonic()
r=subprocess.run([str(binary/'vvp.exe'),str(target),'+frames=135168'],env=env,capture_output=True,text=True,timeout=14400)
record.update(elapsed_seconds=time.monotonic()-t,log=r.stdout+r.stderr,returncode=r.returncode)
if r.returncode or 'PASS' not in r.stdout:
 record['state']='failed';report.write_text(json.dumps(record,indent=2));raise RuntimeError(record['log'])
data=out/'pool_samples.txt';saved=out/f'pool{count}_spectrum_samples.txt';saved.write_bytes(data.read_bytes())
import numpy as np
x=np.loadtxt(saved,dtype=np.float64)[-131072:]
spectrum=np.abs(np.fft.rfft(x))*2/len(x);bins=50+5*np.arange(count)
amplitudes=spectrum[bins]
expected=131071*(60000/65536)*64/count
relative=np.abs(amplitudes-expected)/expected
record.update(state='passed' if np.all(relative<.03) else 'failed',expected_peak_amplitude=float(expected),minimum_peak=float(amplitudes.min()),maximum_peak=float(amplitudes.max()),maximum_relative_error=float(relative.max()),verified_peaks=int(np.count_nonzero(relative<.03)),sample_peak=float(np.max(np.abs(x))),sample_sha256=hashlib.sha256(saved.read_bytes()).hexdigest())
report.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record,indent=2),flush=True)
if record['state']!='passed':raise RuntimeError('Independent coherent spectral peak validation failed')
