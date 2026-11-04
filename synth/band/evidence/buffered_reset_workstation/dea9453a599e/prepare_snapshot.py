"""Combine a verified serializer experiment with an immutable workstation export."""
from pathlib import Path
import argparse,hashlib,json,shutil
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('base',type=Path);ap.add_argument('trial',type=Path);ap.add_argument('clocked_proof',type=Path)
a=ap.parse_args();b=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=a.base.resolve();m=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
for n,h in m['sources'].items():assert sha(base/n)==h,n
trial=json.loads(a.trial.read_text());proof=json.loads(a.clocked_proof.read_text())
source=Path(trial['source_dir'])/'gowin_dvi_tx.v'
assert sha(source)==trial['source_sha256']
assert proof['status']=='passed' and proof['sources']['gowin_dvi_tx.v']==sha(source)
for name in ('gowin_video_clock.v','dvi_symbols.v','starcluster_tmds_encoder.v'):
    assert sha(base/'rtl'/name)==proof['sources'][name],name
digest=hashlib.sha256((sha(base/'export_manifest.json')+sha(source)+sha(a.clocked_proof)).encode()).hexdigest()
target=base.parent/('offline_workstation_reset_buffer_'+digest[:12]);assert not target.exists()
shutil.copytree(base,target);shutil.copy2(source,target/'rtl/gowin_dvi_tx.v')
build_id=int(digest[:8],16);(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
m['build_id']=build_id;m['sources']={n:sha(target/n) for n in m['sources']}
m['reset_buffer_trial']={'status':'experimental_not_release','baseline':str(base),'clocked_proof_sha256':sha(a.clocked_proof),'stages':trial['stages'],'scope':'Clocked serializer functional proof only; fulltop, native recovery/removal, pulse, physical clock and pin review required. No reset false paths authorized.'}
(target/'export_manifest.json').write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Reset buffer experiment: native recovery/removal, setup/hold/pulse and pin audit required before release.\n')
out=b/'evidence/buffered_reset_workstation'/digest[:12];out.mkdir(parents=True)
record={'status':'prepared_not_accepted','target':str(target),'build_id':build_id,'manifest_sha256':sha(target/'export_manifest.json')}
(out/'preparation.json').write_text(json.dumps(record,indent=2));shutil.copy2(__file__,out/'prepare_snapshot.py');print(json.dumps(record,indent=2))
