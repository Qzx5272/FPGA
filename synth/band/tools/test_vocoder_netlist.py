"""Actual synthesized vocoder vs independent reference, vendor primitive models."""
from pathlib import Path
import os,sys,subprocess,json,hashlib,shutil,re,datetime,argparse
r=Path(__file__).resolve().parents[3];b=r/'synth/band'
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('build',type=Path)
ap.add_argument('--reference-json',type=Path,default=b/'evidence/vocoder_core/result.json')
args=ap.parse_args();build=args.build.resolve()
vg=build/'impl/gwsynthesis/vocoder_core.vg';assert vg.is_file()
reference_path=args.reference_json.resolve();prior=reference_path.parent
reference=json.loads(reference_path.read_text());assert reference['status']=='passed'
if 'vectors_sha256' in reference:
 assert hashlib.sha256((prior/'vectors.hex').read_bytes()).hexdigest()==reference['vectors_sha256'],'reference vectors changed'
for name,h in reference['sha256'].items():
 p=build/('coeffs.mem' if name.endswith('.mem') else 'rtl/'+name);assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
out=b/'evidence/vocoder_netlist'/(hashlib.sha256(vg.read_bytes()).hexdigest()[:12]+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir(parents=True,exist_ok=False)
shutil.copy2(vg,out/'vocoder_core.vg')
shutil.copy2(prior/'vectors.hex',out/'vectors.hex')
tb=(prior/'tb.sv').read_text()
tb=tb.replace('module tb;',"module tb;\nGSR GSR(.GSRI(1'b1));")
tb=tb.replace('initial begin\n $readmemh','initial begin\n $display("BEGIN vendor netlist");\n $readmemh')
tb=tb.replace('if(!ready_out)', 'if(n%16==0)$display("PROGRESS n=%0d time=%0t",n,$time);\n  if(!ready_out)')
tb=re.sub(r'vocoder_core #\(\.COEFF_FILE\("[^"]+"\)\)', 'vocoder_core',tb)
tb=tb.replace('n<4096','n<320').replace('if(n==2048)','if(n==256)')
# After reset, use the independent all-zero/rail/decay reference section.
tb=tb.replace('vectors[n*4','vectors[(n<256?n:2048+n-256)*4')
tb=tb.replace('PASS full vocoder4096 samples','PASS vendor-netlist320 samples (256 voiced/noise +64 reset/rail/decay)')
(out/'tb.sv').write_text(tb)
tools=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(tools)+os.pathsep+str(tools.parent/'lib')+os.pathsep+env['PATH']
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
record=dict(status='running',build=str(build),scope='320post-synthesis vocoder samples against independent fixed-point reference;reset/busy/clip/reject checked. Vendor primitive functional simulation,not routed timing or physical audio acceptance',netlist_sha256=hashlib.sha256(vg.read_bytes()).hexdigest(),vendor_sha256=hashlib.sha256(vendor.read_bytes()).hexdigest(),reference=reference)
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(out,flush=True)
try:
 c=subprocess.run([str(tools/'iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),str(vg),str(out/'tb.sv'),str(vendor)],env=env,capture_output=True,text=True,timeout=180)
 (out/'compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,'compile failed'
 with (out/'simulation.log').open('w') as log:
  p=subprocess.run([str(tools/'vvp.exe'),'-i',str(out/'test.vvp')],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
 output=(out/'simulation.log').read_text()
 record.update(status='passed' if p.returncode==0 and 'PASS vendor-netlist320' in output else 'failed',returncode=p.returncode,log=output)
except Exception as exc:
 record.update(status='failed_timeout' if isinstance(exc,subprocess.TimeoutExpired) else 'failed',error=str(exc))
 if (out/'simulation.log').exists():record['log']=(out/'simulation.log').read_text()
 raise
finally:report.write_text(json.dumps(record,indent=2))
print(record['status'],record.get('log',''));raise SystemExit(record['status']!='passed')
