"""Replay packaged vocoder RTL/reference fixtures without the author's build drive."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,subprocess,tempfile

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('evidence',type=Path,help='Folder containing result.json, five sources, tb.sv and vectors.hex')
ap.add_argument('--iverilog',help='Icarus Verilog compiler path; otherwise PATH or local OSS CAD suite')
ap.add_argument('--vvp',help='Icarus runtime path; otherwise beside compiler or PATH')
ap.add_argument('--output',type=Path,help='New output directory; never overwrite old evidence')
a=ap.parse_args()
root=Path(__file__).resolve().parents[3];evidence=a.evidence.resolve()
proof=json.loads((evidence/'result.json').read_text(encoding='utf-8'))
assert proof['status']=='passed_rtl_and_synthesis_only', 'Expected completed isolated RTL/synthesis fixture'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in proof['sources'].items():
    assert Path(n).name==n and sha(evidence/n)==h, 'Source changed: '+n
assert sha(evidence/'vectors.hex')==proof['vectors_sha256'], 'Reference vectors changed'
local=root/'tmp/oss-cad-suite/bin/iverilog.exe'
compiler=Path(a.iverilog or shutil.which('iverilog') or (str(local) if local.exists() else ''))
if not compiler.is_file():ap.error('Install Icarus Verilog and supply --iverilog, or add it to PATH')
compiler=compiler.resolve()
runtime=Path(a.vvp) if a.vvp else compiler.with_name('vvp'+compiler.suffix)
if not runtime.is_file():runtime=Path(shutil.which('vvp') or '')
if not runtime.is_file():ap.error('Cannot find vvp; supply --vvp')
runtime=runtime.resolve()
if a.output:
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
else:out=Path(tempfile.mkdtemp(prefix='starcluster_vocoder_replay_'))
names=list(proof['sources'])+['tb.sv','vectors.hex']
for n in names:shutil.copy2(evidence/n,out/n)
env=dict(os.environ)
env['PATH']=str(compiler.parent)+os.pathsep+str(compiler.parent.parent/'lib')+os.pathsep+env.get('PATH','')
record={'status':'running','started':datetime.datetime.now().isoformat(),
        'scope':'4096-sample isolated RTL replay against packaged independent reference; no synthesis, whole-band, timing or board claim',
        'sources':{n:sha(out/n) for n in names},'original_report_sha256':sha(evidence/'result.json'),
        'tools':{'iverilog':str(compiler),'vvp':str(runtime)}}
report=out/'replay_result.json'
report.write_text(json.dumps(record,indent=2));print(str(out),flush=True)
try:
    files=[n for n in proof['sources'] if n.endswith(('.sv','.v'))]
    c=subprocess.run([str(compiler),'-g2012','-s','tb','-o','test.vvp',*files,'tb.sv'],cwd=out,env=env,capture_output=True,text=True,timeout=120)
    (out/'compile.log').write_text(c.stdout+c.stderr)
    assert c.returncode==0,'Compilation failed'
    with (out/'simulation.log').open('w') as log:
        p=subprocess.run([str(runtime),'test.vvp'],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
    log=(out/'simulation.log').read_text()
    assert p.returncode==0 and 'PASS full vocoder4096 samples' in log, 'Reference replay failed'
    record.update(status='passed',log=log)
except Exception as exc:
    record.update(status='failed',error=str(exc));raise
finally:
    record['finished']=datetime.datetime.now().isoformat()
    report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
