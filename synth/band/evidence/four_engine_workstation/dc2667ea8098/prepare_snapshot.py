"""Freeze an experimental full-song export; no release or board claim."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('base',type=Path)
ap.add_argument('candidate',type=Path,help='Isolated RTL and synthesis result')
ap.add_argument('integration',type=Path,help='Exported 256-slot/singer integration result')
ap.add_argument('pixel_export',type=Path,help='Previously tested pixel reset export')
a=ap.parse_args()
band=Path(__file__).resolve().parents[1];root=band.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=a.base.resolve();pixel=a.pixel_export.resolve()
manifest=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for n,h in manifest['sources'].items():assert sha(base/n)==h,n
candidate=json.loads(a.candidate.read_text())
assert candidate['status']=='passed_rtl_and_synthesis_only'
build=Path(candidate['build'])
from vocoder_gate import require_vocoder_gate
netlist=require_vocoder_gate(build)
integration=json.loads(a.integration.read_text())
assert integration['status']=='passed' and Path(integration['export'])==base
assert integration['vocoder_candidate'] and Path(integration['vocoder_candidate']).resolve()==a.candidate.resolve()
for n,h in integration['sources'].items():assert sha(root/n)==h,n
reset=pixel/'rtl/gowin_dvi_tx.v'
assert sha(reset)=='1320b5fb12aacb57e89d77db6d84aa32f09c03e8ea98a107af80ca597f8b3576'
digest=hashlib.sha256((sha(base/'export_manifest.json')+sha(a.candidate)+sha(a.integration)+sha(reset)).encode()).hexdigest()
target=base.parent/('offline_workstation_four_engine_'+digest[:12])
assert not target.exists(), 'Preserve existing export'
shutil.copytree(base,target)
for name,h in candidate['sources'].items():
    rel=Path(name if name.endswith('.mem') else 'rtl/'+name)
    assert sha(build/rel)==h,name
    shutil.copy2(build/rel,target/rel)
    manifest['sources'][rel.as_posix()]=h
shutil.copy2(reset,target/'rtl/gowin_dvi_tx.v')
build_id=int(digest[:8],16)
(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
manifest['build_id']=build_id
manifest['sources']={n:sha(target/n) for n in manifest['sources']}
manifest['four_engine_trial']={
    'status':'experimental_not_release','created':datetime.datetime.now().isoformat(),
    'baseline':str(base),'integration':str(a.integration.resolve()),
    'integration_sha256':sha(a.integration),'netlist_gate':netlist,
    'reset_source':str(reset),'reset_sha256':sha(reset),
    'scope':'Actual singer acceptance score, four-engine vocoder, pixel reset. Fulltop, PnR, physical audio and board acceptance pending.'}
(target/'export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Experimental integration. Fullchain, buttons, synthesis, native timing and fixed-pin release audit required.\n')
out=band/'evidence/four_engine_workstation'/digest[:12];out.mkdir(parents=True)
record={'status':'prepared_not_accepted','target':str(target),'build_id':build_id,'manifest_sha256':sha(target/'export_manifest.json'),'production_adopted':False}
(out/'preparation.json').write_text(json.dumps(record,indent=2))
shutil.copy2(__file__,out/'prepare_snapshot.py')
print(json.dumps(record,indent=2))
