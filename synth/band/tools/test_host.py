"""Run host interaction regression and retain exact-source evidence."""
from pathlib import Path
import subprocess,sys,json,hashlib,datetime,os
def main():
    root=Path(__file__).resolve().parents[3];band=root/'synth/band'
    sources=list((band/'host').glob('*.py'))+list((band/'tests').glob('test_*.py'))
    env=dict(os.environ);env['QT_QPA_PLATFORM']='offscreen'
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(band/'tests'),'-p','test_*.py','-v'],cwd=root,env=env,capture_output=True,text=True)
    record=dict(status='passed' if r.returncode==0 else 'failed',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                sources={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},output=r.stdout+r.stderr,returncode=r.returncode,
                driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (band/'evidence/host_tests.json').write_text(json.dumps(record,indent=2));print(record['output'])
    return r.returncode


if __name__ == '__main__':
    raise SystemExit(main())
