"""Check the isolated candidate's full vocoder PCM, then synthesize without pins."""
from pathlib import Path
import hashlib,json,shutil,subprocess,datetime,os,re
band=Path(__file__).resolve().parents[1];root=band.parents[1]
proof_path=band/'evidence/filterbank_four_engines/20261026_202623/result.json'
proof=json.loads(proof_path.read_text());assert proof['status']=='passed'
candidate=Path(proof['candidate']);baseline=band/'release/pt8211_dvi_062a944dcce1/source_snapshot'
names=('filterbank.sv','double_biquad.sv','vocoder_core.sv','vocoder_mixer.sv','coeffs.mem')
sources={n:(candidate/n if (candidate/n).exists() else baseline/n) for n in names}
for n in ('filterbank.sv','double_biquad.sv','coeffs.mem'):
 assert hashlib.sha256(sources[n].read_bytes()).hexdigest()==proof['source_sha256'][str(sources[n].relative_to(root))]
hashes={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in sources.items()}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=Path('D:/StarclusterBuilds')/('vocoder_four_syn_'+digest);out=band/'evidence/vocoder_four_engines'/digest
if build.exists() or out.exists():raise ValueError('Preserve existing run')
(build/'rtl').mkdir(parents=True);out.mkdir(parents=True)
for n,p in sources.items():
 shutil.copy2(p,build/('coeffs.mem' if n.endswith('.mem') else 'rtl/'+n));shutil.copy2(p,out/n)
prior=band/'evidence/vocoder_core';shutil.copy2(prior/'vectors.hex',out/'vectors.hex')
tb=(prior/'tb.sv').read_text().replace('if(cycles>200)','if(cycles>1000)')
tb=re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("coeffs.mem")',tb);(out/'tb.sv').write_text(tb)
(build/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module vocoder_core
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
foreach f [glob rtl/*.sv] {add_file $f}
set_option -output_base_name vocoder_core
run syn
''')
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
report=out/'result.json';record=dict(status='running',sources=hashes,build=str(build),started=datetime.datetime.now().isoformat(),vectors_sha256=hashlib.sha256((out/'vectors.hex').read_bytes()).hexdigest(),scope='Isolated four-engine vocoder RTL and synthesis; no vendor-netlist/full-band/PnR/board claim')
report.write_text(json.dumps(record,indent=2));print(str(report),flush=True)
try:
 with (out/'compile.log').open('w') as log:
  r=subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-s','tb','-o',str(out/'sim.vvp'),*map(str,(build/'rtl').glob('*.sv')),str(out/'tb.sv')],env=env,stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0,'RTL compilation failed'
 with (out/'simulation.log').open('w') as log:
  r=subprocess.run([str(cad/'bin/vvp.exe'),str(out/'sim.vvp')],env=env,cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 record['rtl_log']=(out/'simulation.log').read_text()
 assert r.returncode==0 and 'PASS full vocoder4096' in record['rtl_log'],record['rtl_log']
 record['status']='passed_rtl_synthesis_running';report.write_text(json.dumps(record,indent=2));print(record['rtl_log'],flush=True)
 with (build/'build.log').open('w') as log:
  r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=900)
 vg=build/'impl/gwsynthesis/vocoder_core.vg'
 assert r.returncode==0 and vg.exists() and 'ERROR' not in (build/'build.log').read_text(),'Synthesis failed'
 record.update(status='passed_rtl_and_synthesis_only',netlist_sha256=hashlib.sha256(vg.read_bytes()).hexdigest())
except Exception as exc:
 record.update(status='failed',error=str(exc));raise
finally:
 for p in (build/'impl/gwsynthesis').glob('*.html'):shutil.copy2(p,out/p.name)
 shutil.copy2(build/'build.tcl',out/'build.tcl')
 if (build/'build.log').exists():shutil.copy2(build/'build.log',out/'build.log')
 record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
