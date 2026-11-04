"""Audit release hashes and attach only exact matching frozen diagnostic sources."""
from pathlib import Path
import json,hashlib,shutil
from verify_fs import verify_fs
band=Path(__file__).resolve().parents[1];rows=[]
hardware_path=band/'evidence/hardware_band.json'
hardware=json.loads(hardware_path.read_text()) if hardware_path.exists() else {}
failed_board_hashes=set()
passed_board_hashes=set()
for path in list((band/'evidence').glob('hardware_band*.json'))+list((band/'evidence').glob('hardware_pt8211_dvi_*.json')):
 record=json.loads(path.read_text())
 if record.get('status')=='failed':failed_board_hashes.add(record.get('bitstream_sha256'))
 if record.get('status')=='passed' and record.get('stress_active_notes')==256 and record.get('automatic_test_seconds',0)>=97:
  passed_board_hashes.add(record.get('bitstream_sha256'))
for manifest_path in sorted((band/'release').glob('*/manifest.json')):
 release=manifest_path.parent;m=json.loads(manifest_path.read_text(encoding='utf-8'));bitstreams=list(release.glob('*.fs'))
 if len(bitstreams)!=1:raise RuntimeError('Expected one bitstream: '+str(release))
 bitstream=bitstreams[0]
 verify_fs(bitstream)
 if hashlib.sha256(bitstream.read_bytes()).hexdigest()!=m['bitstream_sha256']:raise RuntimeError('Bitstream hash mismatch: '+str(release))
 if m.get('setup_violations')!=0 or m.get('hold_violations')!=0:raise RuntimeError('Not timing-clean: '+str(release))
 checked=0
 if release.name.startswith('diagnostic'):
  snapshot=release/'source_snapshot'
  if not snapshot.exists():snapshot=band/'build'/release.name/'source_snapshot'
  for name,digest in m['sources'].items():
   if hashlib.sha256((snapshot/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Diagnostic source snapshot changed: '+str(snapshot/name))
   checked+=1
  if snapshot!=release/'source_snapshot':shutil.copytree(snapshot,release/'source_snapshot',dirs_exist_ok=True)
  for suffix in ('rpt.txt','timing_paths','log'):
   p=band/'build'/release.name/'impl/pnr'/(release.name+'.'+suffix)
   if p.exists():shutil.copy2(p,release/p.name)
 elif m.get('snapshot_sha256'):
  for name,digest in m['snapshot_sha256'].items():
   if hashlib.sha256((release/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Release source changed: '+name)
   checked+=1
 elif release.name=='v4a_20261022':
  for relative,digest in m['source_sha256'].items():
   # Historical archive preserves the original synth-relative path.
   p=release/'source'/Path(relative.replace('\\','/'))
   if not p.exists():p=release/'source'/Path(relative.replace('\\','/')).name
   if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('Historical snapshot mismatch '+str(p))
   checked+=1
 elif m.get('source_sha256'):
  snapshot=band/'build'/release.name/'source_snapshot'
  verified={}
  for relative,digest in m['source_sha256'].items():
   name=Path(relative.replace('\\','/')).name;p=snapshot/name
   if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise RuntimeError('Legacy frozen source mismatch: '+str(p))
   verified[name]=digest;checked+=1
  shutil.copytree(snapshot,release/'source_snapshot',dirs_exist_ok=True)
  m['snapshot_sha256']=verified
  manifest_path.write_text(json.dumps(m,indent=2))
  for suffix in ('rpt.txt','timing_paths','log'):
   p=band/'build'/release.name/'impl/pnr'/('starcluster_band.'+suffix)
   if p.exists():shutil.copy2(p,release/p.name)
 if checked==0:raise RuntimeError('No exact source provenance checked: '+str(release))
 board='failed' if m['bitstream_sha256'] in failed_board_hashes else 'passed_digital_only' if m['bitstream_sha256'] in passed_board_hashes else 'not_verified'
 rows.append(dict(release=release.name,bitstream_sha256=m['bitstream_sha256'],exact_source_files_verified=checked,setup_violations=0,hold_violations=0,board_validation=board))
(band/'evidence/release_audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
