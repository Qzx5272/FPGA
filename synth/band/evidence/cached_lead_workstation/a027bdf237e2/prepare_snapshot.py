"""Freeze a lead-cache experiment after invariant and full-core integration checks."""
from pathlib import Path
import argparse,hashlib,json,shutil
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('proof',type=Path);ap.add_argument('integration',type=Path);a=ap.parse_args()
b=Path(__file__).resolve().parents[1];root=b.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads(a.proof.read_text());i=json.loads(a.integration.read_text())
assert p['status']==i['status']=='passed'
assert Path(i['allocator_candidate']).resolve()==a.proof.resolve()
for n,h in i['sources'].items():assert sha(root/n)==h,n
base=Path(i['export']);m=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for n,h in m['sources'].items():assert sha(base/n)==h,n
source=Path(p['candidate']);assert sha(source)==p['candidate_sha256']
assert sha(base/'rtl/shared_note_allocator.v')==p['baseline_sha256']
digest=hashlib.sha256((sha(base/'export_manifest.json')+sha(source)+sha(a.integration)).encode()).hexdigest()
target=base.parent/('offline_workstation_cached_lead_'+digest[:12]);assert not target.exists()
shutil.copytree(base,target);shutil.copy2(source,target/'rtl/shared_note_allocator.v')
build_id=int(digest[:8],16);(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
m['build_id']=build_id;m['sources']={n:sha(target/n) for n in m['sources']}
m['cached_lead_trial']={'status':'experimental_not_release','baseline':str(base),'proof_sha256':sha(a.proof),'integration_sha256':sha(a.integration),'scope':'Exact lead-bit identity RTL invariant and64frame full-core test; synthesis, fulltop, timing, physical acceptance pending'}
(target/'export_manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Cached lead experiment: fulltop, synthesis, timing, pin audit and physical acceptance pending.\n')
out=b/'evidence/cached_lead_workstation'/digest[:12];out.mkdir(parents=True)
record={'status':'prepared_not_accepted','target':str(target),'build_id':build_id,'manifest_sha256':sha(target/'export_manifest.json')}
(out/'preparation.json').write_text(json.dumps(record,indent=2));shutil.copy2(__file__,out/'prepare_snapshot.py');print(json.dumps(record,indent=2))
