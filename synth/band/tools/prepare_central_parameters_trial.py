"""Freeze centralized role parameters after bounded exact stereo/control proof."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil
band=Path(__file__).resolve().parents[1];root=band.parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('proof',type=Path);a=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads(a.proof.read_text());assert proof['status']=='passed'
assert any(t['top']=='tb_central_parameters' and t['passed'] for t in proof['tests'])
for name,h in proof['sources'].items():assert sha(root/name)==h,('Changed tested source',name)
base=root/'output/final_workstation_20261022/offline_workstation_pt8211_shared_c38c151eeea4'
manifest=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['sources'].items():assert sha(base/name)==h,('Changed baseline',name)
source=band/'experimental/shared_voices';candidate=source/'central_parameters'
assert (base/'rtl/band_singer_core.sv').read_text()==(source/'shared_band_singer_core.sv').read_text().replace('module shared_band_singer_core #','module band_singer_core #')
for name in ('shared_note_allocator.v','shared_band_renderer.v','shared_bank_dispatch.v','shared_voice_bank.v'):
    assert (base/'rtl'/name).read_bytes()==(source/name).read_bytes()
names=['shared_role_controls.v','central_voice_bank.v','central_band_singer_core.sv']
digest=hashlib.sha256((sha(base/'export_manifest.json')+''.join(sha(candidate/n) for n in names)).encode()).hexdigest()
target=base.parent/('offline_workstation_pt8211_central_'+digest[:12]);assert not target.exists()
shutil.copytree(base,target)
for name in names:
    assert proof['sources'][str((candidate/name).relative_to(root))]==sha(candidate/name)
    if name=='central_band_singer_core.sv':
        (target/'rtl/band_singer_core.sv').write_text((candidate/name).read_text().replace('module central_band_singer_core #','module band_singer_core #'))
    else:
        shutil.copyfile(candidate/name,target/'rtl'/name);manifest['sources']['rtl/'+name]=sha(target/'rtl'/name)
build_id=int(digest[:8],16);assert build_id!=manifest['build_id']
(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
manifest['build_id']=build_id;manifest['sources']={n:sha(target/n) for n in manifest['sources']}
manifest['central_parameters_trial']=dict(status='experimental_not_release',created=datetime.datetime.now().isoformat(),baseline=str(base),proof=str(a.proof.resolve()),proof_sha256=sha(a.proof),scope='One patch/slew state per role;bounded64frame exact reference comparison only;resources/timing/fulltop/board pending')
(target/'export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Central role parameter experiment: fullchain,resource,timing and fixedpin gates required. Not a release.\n')
out=band/'evidence/central_parameters_trial'/digest[:12];out.mkdir(parents=True)
record=dict(status='prepared',target=str(target),build_id=build_id,manifest_sha256=sha(target/'export_manifest.json'),production_adopted=False)
(out/'preparation.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
