"""Observe failed candidate band outputs; diagnostic only, never an acceptance test."""
from pathlib import Path
import os,re,json,hashlib,subprocess,shutil,datetime,argparse
from vocoder_reference import Cascade

band=Path(__file__).resolve().parents[1];root=band.parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('prior',type=Path)
parser.add_argument('build',type=Path)
args=parser.parse_args();prior=args.prior.resolve();source=args.build.resolve()
out=band/'evidence/vocoder_four_diagnosis'/datetime.datetime.now().strftime('%Y%m%d_%H%M%S');out.mkdir(parents=True)
shutil.copy2(Path(__file__),out/'diagnostic_driver_snapshot.py')
tb=(prior/'tb.sv').read_text().replace('n<320','n<8')
tb=re.sub(r'  if\(sample_out!==[^\n]+\)\n   \$fatal\([^\n]+\);','',tb)
assert 'sample %0d got' not in tb
trace='\n'.join(f'  $display("BAND %0d {i} %0d %0d",n,$signed(dut.\\carrier[{i}] ),$signed(dut.\\envelope[{i}] ));' for i in range(16))
tb=tb.replace('  if(cycles>maximum)',trace+'\n  if(cycles>maximum)')
tb=tb.replace('PASS vendor-netlist320 samples (256 voiced/noise +64 reset/rail/decay)', 'DIAGNOSTIC ONLY eight samples; acceptance checks removed')
(out/'tb.sv').write_text(tb);shutil.copy2(prior/'vectors.hex',out/'vectors.hex')
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
vg=source/'impl/gwsynthesis/vocoder_core.vg';vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
record=dict(status='running_diagnostic',scope='Eight-sample intermediate trace of failed netlist, not acceptance',netlist_sha256=hashlib.sha256(vg.read_bytes()).hexdigest())
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(str(report),flush=True)
with (out/'compile.log').open('w') as log:
 r=subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),str(vg),str(out/'tb.sv'),str(vendor)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
assert r.returncode==0,'compile failed'
with (out/'simulation.log').open('w') as log:
 r=subprocess.run([str(cad/'bin/vvp.exe'),str(out/'test.vvp')],env=env,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
signed=lambda x:x-(1<<32) if x&(1<<31) else x
coeffs=[[signed(int(x,16)) for x in line.split()] for line in (source/'coeffs.mem').read_text().splitlines()]
filters=[[Cascade(coeffs[i]),Cascade(coeffs[16]),Cascade(coeffs[i])] for i in range(16)]
vectors=[signed(int(x,16)) for x in (out/'vectors.hex').read_text().split()]
expected={}
for n in range(8):
 for i,(m,e,c) in enumerate(filters):
  mod=m.step(vectors[n*4]);envelope=e.step(min(abs(mod),2147483647));carrier=c.step(vectors[n*4+1]);expected[n,i]=(carrier,envelope)
observed={}
for n,i,c,e in re.findall(r'BAND (\d+) (\d+) (-?\d+) (-?\d+)',(out/'simulation.log').read_text()):observed[int(n),int(i)]=(int(c),int(e))
diff=[dict(sample=n,band=i,expected=list(value),observed=list(observed.get((n,i),()))) for (n,i),value in expected.items() if observed.get((n,i))!=value]
record.update(status='diagnosis_complete' if r.returncode==0 and len(observed)==128 else 'diagnosis_incomplete',observations=len(observed),mismatch_count=len(diff),mismatches=diff)
report.write_text(json.dumps(record,indent=2));print(json.dumps(dict(status=record['status'],mismatches=diff[:12]),indent=2))
