"""Actual electronic-singer/shared256 integration; not fulltop/PnR."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,shutil
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--export',type=Path,help='Test actual exported band_singer_core instead of historical experimental core')
ap.add_argument('--mixed-load',action='store_true',help='Eight instrument roles plus singer/effect at exact50MHz/48kHz cadence')
ap.add_argument('--vocoder-candidate',type=Path,help='Isolated RTL/synthesis proof JSON; experimental integration only')
ap.add_argument('--allocator-candidate',type=Path,help='Cached-lead invariant proof JSON; experimental integration only')
args=ap.parse_args()
if args.vocoder_candidate and not args.export:ap.error('--vocoder-candidate requires --export')
if args.allocator_candidate and not args.export:ap.error('--allocator-candidate requires --export')
band=Path(__file__).resolve().parents[1];root=band.parents[1]
source=band/'experimental/shared_voices'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=band/'evidence/shared_singer_core'/stamp;out.mkdir(parents=True)
cad=root/'tmp/oss-cad-suite';env=dict(os.environ)
env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH']
base=root/'output/final_workstation_20261022/offline_workstation_pt8211_reset_release'
if args.export:base=args.export.resolve()
manifest=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for n,h in manifest['sources'].items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
files=[p for p in (base/'rtl').iterdir() if p.suffix in ('.v','.sv')]+[p for p in source.glob('shared_*') if p.suffix in ('.v','.sv')]
tests=[('tb_shared_singer_core',source/'tb_shared_singer_core.sv')]
if args.mixed_load:tests=[('tb_shared_singer_core',source/'tb_shared_singer_mixed.sv')]
if args.export:
    files=[p for p in (base/'rtl').iterdir() if p.suffix in ('.v','.sv')]
    tb_text=tests[0][1].read_text().replace('shared_band_singer_core dut','band_singer_core dut')
    assert 'dut.banks[b].unit.target_expression[7]' in tb_text
    tb_text=tb_text.replace('dut.banks[b].unit.target_expression[7]','dut.role_controls.target_expression[7]')
    tb_path=out/'tb_exported_singer_core.sv';tb_path.write_text(tb_text)
    tests=[('tb_shared_singer_core',tb_path)]
if args.vocoder_candidate:
    proof=json.loads(args.vocoder_candidate.read_text())
    assert proof['status']=='passed_rtl_and_synthesis_only'
    candidate=Path(proof['build']); replacements={}
    for name,h in proof['sources'].items():
        p=candidate/('coeffs.mem' if name.endswith('.mem') else 'rtl/'+name)
        assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
        if name.endswith('.mem'):
            assert hashlib.sha256((base/name).read_bytes()).hexdigest()==h,'Coefficient mismatch'
        else:
            dest=out/name;shutil.copy2(p,dest);replacements[name]=dest
    assert set(replacements)<=set(p.name for p in files)
    files=[replacements.get(p.name,p) for p in files]
if args.allocator_candidate:
    proof=json.loads(args.allocator_candidate.read_text())
    assert proof['status']=='passed'
    p=Path(proof['candidate'])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==proof['candidate_sha256']
    assert hashlib.sha256((base/'rtl/shared_note_allocator.v').read_bytes()).hexdigest()==proof['baseline_sha256']
    dest=out/'shared_note_allocator.v';shutil.copy2(p,dest)
    files=[dest if p.name=='shared_note_allocator.v' else p for p in files]
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
    scope='Actual shared_band_singer_core:256 choir slots plus dedicated part15 electronic singer64samples at1042clocks/sample; controls,duplicate/full/tails,broadcast source loss reaching both paths,next-bar ownership return(injected bar),panic. No complete song,DVI,synthesis,timing,acoustic or board claim.',
    sources={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in hashfiles},tests=results,production_adopted=False)
record['export']=str(base)
record['vocoder_candidate']=str(args.vocoder_candidate) if args.vocoder_candidate else None
record['allocator_candidate']=str(args.allocator_candidate) if args.allocator_candidate else None
record['scope']+=' Export override tests current central role controls. Candidate replacement is experimental RTL integration only, not release adoption.' if args.export else ''
if args.mixed_load:
    record['scope']='Mixed-role RTL only:32 notes on each of roles0..7 plus dedicated singer and wet32 delay;512 output frames at exact50MHz/48kHz tick cadence; initial256 allocated slots, sustained slot count reported; source-loss and panic. No board, acoustic, long-duration or performance-ceiling claim.'
(out/'result.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(dict(status=record['status'],report=str(out/'result.json'),tests=results),indent=2))
if record['status']!='passed':raise SystemExit(1)
