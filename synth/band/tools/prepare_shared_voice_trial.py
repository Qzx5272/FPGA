"""Freeze shared-voice fulltop experiment after source-matched core RTL proof."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil
band=Path(__file__).resolve().parents[1];root=band.parents[1]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('proof',type=Path);a=ap.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads(a.proof.read_text());assert proof['status']=='passed'
assert any(t.get('top')=='tb_shared_singer_core' and t.get('passed') for t in proof.get('tests',[])), 'Require actual singer-core path proof'
for path,h in proof['sources'].items():assert sha(root/path)==h,('Changed tested source',path)
base=root/'output/final_workstation_20261022/offline_workstation_pt8211_reset_release'
m=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in m['sources'].items():assert sha(base/name)==h,('Changed base',name)
assert (base/'rtl/band_core.v').read_text()==(band/'rtl/band_core.v').read_text(),'Review base core divergence (line endings normalized)'
exp=band/'experimental/shared_voices'
names=['shared_bank_dispatch.v','shared_note_allocator.v','shared_voice_bank.v','shared_band_renderer.v','shared_band_core.v','shared_band_singer_core.sv']
signature=hashlib.sha256((sha(base/'export_manifest.json')+''.join(sha(exp/n) for n in names)).encode()).hexdigest()
target=base.parent/('offline_workstation_pt8211_shared_'+signature[:12])
assert not target.exists(),'Preserve existing experiment'
shutil.copytree(base,target)
for name in names:
    assert proof['sources'][(exp/name).relative_to(root).as_posix().replace('/', '\\')]==sha(exp/name)
    if name=='shared_band_core.v':
        (target/'rtl/band_core.v').write_text((exp/name).read_text().replace('module shared_band_core #','module band_core #'))
    elif name=='shared_band_singer_core.sv':
        (target/'rtl/band_singer_core.sv').write_text((exp/name).read_text().replace('module shared_band_singer_core #','module band_singer_core #'))
    else:
        shutil.copyfile(exp/name,target/'rtl'/name)
        m['sources']['rtl/'+name]=sha(target/'rtl'/name)
build_id=int(signature[:8],16);assert build_id!=m['build_id']
assert 'band_singer_core #' in (target/'rtl/band_singer_board_engine.sv').read_text()
assert 'shared_voice_bank unit' in (target/'rtl/band_singer_core.sv').read_text()
assert 'voice_bank #(' not in (target/'rtl/band_singer_core.sv').read_text()
(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
m['build_id']=build_id;m['sources']={n:sha(target/n) for n in m['sources']}
m['shared_voice_trial']=dict(status='experimental_not_release',created=datetime.datetime.now().isoformat(),baseline=str(base),proof=str(a.proof.resolve()),proof_sha256=sha(a.proof),scope='All-role banks and two-phase global allocation; per-role stereo. Short RTL core proof only; fulltop/resources/timing/board pending.')
(target/'export_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Shared voice experimental export. No release or physical programming before fullchain, timing and fixedpin gates.\n')
out=band/'evidence/shared_voice_trial'/signature[:12];out.mkdir(parents=True)
record=dict(status='prepared',target=str(target),build_id=build_id,manifest_sha256=sha(target/'export_manifest.json'),production_adopted=False)
(out/'preparation.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
