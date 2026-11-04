"""Behavioral integration gate for experimental shared256 core; not fulltop/PnR."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess
band=Path(__file__).resolve().parents[1];root=band.parents[1]
source=band/'experimental/shared_voices'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=band/'evidence/shared_core'/stamp;out.mkdir(parents=True)
cad=root/'tmp/oss-cad-suite';env=dict(os.environ)
env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
files=list((band/'rtl').glob('*.v'))+list(source.glob('shared_*.v'))+[root/'synth/rtl/hq_sine_quarter.v']
tests=[('tb_shared_core',source/'tb_shared_core.sv'),('tb_controls',source/'tb_shared_controls.v')]
results=[]
for top,tb in tests:
    compile=subprocess.run([str(cad/'bin/iverilog.exe'),'-g2012','-I',str(band/'rtl'),'-I',str(root/'synth/rtl'),'-s',top,'-o',str(out/(top+'.vvp')),*map(str,files),str(tb)],env=env,capture_output=True,text=True,timeout=60)
    sim=None
    if compile.returncode==0:
        sim=subprocess.run([str(cad/'bin/vvp.exe'),str(out/(top+'.vvp'))],env=env,capture_output=True,text=True,timeout=120)
    passed=compile.returncode==0 and sim is not None and sim.returncode==0 and 'PASS' in sim.stdout
    results.append(dict(top=top,passed=passed,compile=compile.stdout+compile.stderr,simulation=sim.stdout+sim.stderr if sim else 'not run'))
hashfiles=files+[p for _,p in tests]+list((band/'rtl').glob('*.vh'))+[root/'synth/rtl/sine_quarter_init.vh',Path(__file__)]
record=dict(status='passed' if all(r['passed'] for r in results) else 'failed',created=datetime.datetime.now().isoformat(),
    scope='Shared musical core:256 choir voices64samples at1042clocks/sample, control broadcast, duplicate/full/tails, immediate source release and next-bar ownership return (injected bar), panic; ownership/epoch control rejection and score/host parameter arbitration. No complete song, external singer/DVI, synthesis, timing, acoustic or board claim.',
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in hashfiles},tests=results,production_adopted=False)
(out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(dict(status=record['status'],report=str(out/'result.json'),tests=results),indent=2))
if record['status']!='passed':raise SystemExit(1)
