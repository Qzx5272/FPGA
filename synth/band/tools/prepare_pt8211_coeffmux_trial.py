"""Freeze a full-board coefficient-selection trial without changing the release."""
from pathlib import Path
import datetime,hashlib,json,shutil

band=Path(__file__).resolve().parents[1]
root=band.parents[1]
base=root/'output/final_workstation_20261022/offline_workstation_pt8211_dvi_confluence'
experiment=band/'evidence/vocoder_coeffmux/b0b2563dabe7'
manifest=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))
proof=json.loads((experiment/'rtl_result.json').read_text())
original=json.loads((experiment/'result.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if proof['status']!='passed':raise RuntimeError('Missing isolated numerical gate')
for name,digest in manifest['sources'].items():
    if sha(base/name)!=digest:raise RuntimeError('Baseline changed: '+name)
for name,digest in original['baseline_sources'].items():
    path=base/name if name.endswith('.mem') else base/'rtl'/name
    if sha(path)!=digest:raise RuntimeError('Isolated baseline differs from full export: '+name)
for name,digest in proof['sha256'].items():
    if sha(experiment/name)!=digest:raise RuntimeError('Numerical candidate changed: '+name)
candidate_sha=sha(experiment/'filterbank.sv')
trial_id=hashlib.sha256((sha(base/'export_manifest.json')+candidate_sha).encode()).hexdigest()
target=base.parent/('offline_workstation_pt8211_coeffmux_'+trial_id[:12])
if target.exists():raise RuntimeError('Preserve existing trial: '+str(target))
shutil.copytree(base,target)
shutil.copyfile(experiment/'filterbank.sv',target/'rtl/filterbank.sv')
build_id=int(trial_id[:8],16)
if build_id==manifest['build_id']:raise RuntimeError('Trial ID collision')
(target/'rtl/build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{build_id:08x}\n")
manifest['build_id']=build_id
manifest['sources']={n:sha(target/n) for n in manifest['sources']}
manifest['optimization_trial']=dict(baseline=str(base),baseline_manifest_sha256=sha(base/'export_manifest.json'),
    change='filterbank coefficient holding registers replaced by combinational row selection',
    isolated_proof=str(experiment/'rtl_result.json'),isolated_proof_sha256=sha(experiment/'rtl_result.json'),
    status='experimental_not_release',created=datetime.datetime.now().isoformat(),
    limits='Only isolated numerical evidence; no full-board equivalence, resource reduction, timing or hardware claim')
(target/'export_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(target/'NOT_PROGRAMMABLE.txt').write_text('Optimization trial only. Do not program until full-chain, timing and fixed-pin release gates pass.\n')
record=dict(status='prepared',target=str(target),build_id=build_id,
    changed_source_files=[n for n,h in manifest['sources'].items() if h!=json.loads((base/'export_manifest.json').read_text(encoding='utf-8'))['sources'][n]],
    trial_manifest_sha256=sha(target/'export_manifest.json'),release_changed=False)
out=band/'evidence/pt8211_coeffmux';out.mkdir(exist_ok=True)
(out/'preparation.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
