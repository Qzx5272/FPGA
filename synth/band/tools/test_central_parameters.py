"""Actual electronic-singer/shared256 integration; not fulltop/PnR."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess
band=Path(__file__).resolve().parents[1];root=band.parents[1]
source=band/'experimental/shared_voices'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=band/'evidence/central_parameters'/stamp;out.mkdir(parents=True)
cad=root/'tmp/oss-cad-suite';env=dict(os.environ)
env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
base=root/'output/final_workstation_20261022/offline_workstation_pt8211_reset_release'
manifest=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for n,h in manifest['sources'].items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
files=[p for p in (base/'rtl').iterdir() if p.suffix in ('.v','.sv')]+[p for p in source.glob('shared_*') if p.suffix in ('.v','.sv')]
files += [p for p in (source/'central_parameters').iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]
tests=[('tb_central_parameters',source/'central_parameters/tb_central_parameters.sv')]
results=[]
for top,tb in tests:
    compile=subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-I',str(base/'rtl'),'-I',str(root/'synth/rtl'),'-s',top,'-o',str(out/(top+'.vvp')),*map(str,files),str(tb)],env=env,capture_output=True,text=True,timeout=60)
    sim=None
    if compile.returncode==0:
        sim=subprocess.run([str(cad/'bin/vvp.exe'),str(out/(top+'.vvp'))],cwd=base,env=env,capture_output=True,text=True,timeout=120)
    passed=compile.returncode==0 and sim is not None and sim.returncode==0 and 'PASS' in sim.stdout
    results.append(dict(top=top,passed=passed,compile=compile.stdout+compile.stderr,simulation=sim.stdout+sim.stderr if sim else 'not run'))
hashfiles=files+[p for _,p in tests]+list((base/'rtl').glob('*.vh'))+list(base.glob('*.mem'))+[Path(__file__)]
record=dict(status='passed' if all(r['passed'] for r in results) else 'failed',created=datetime.datetime.now().isoformat(),
    scope='Centralized parameters compared cycle-for-cycle with replicated shared singer core:256choir+part15,64stereo frames,expression/bend/vowel/envelope changes,duplicate/tails/source release and synchronized bar injection,panic. Exact PCM/control equality in this bounded test only; no resource/timing/fullsong/board claim.',
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in hashfiles},tests=results,production_adopted=False)
(out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(dict(status=record['status'],report=str(out/'result.json'),tests=results),indent=2))
if record['status']!='passed':raise SystemExit(1)
