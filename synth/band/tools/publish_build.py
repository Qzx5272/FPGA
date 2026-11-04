"""Publish only a timing-clean V4 candidate; keep V2 untouched."""
raise SystemExit('Retired: use tools/build_band.py, which builds and publishes an immutable source snapshot. This historical publisher must not attach current sources to an old bitstream.')
from pathlib import Path
import re,json,hashlib,shutil,datetime
band=Path(__file__).resolve().parents[1];pnr=band/'build/band/impl/pnr'
timing=(pnr/'starcluster_band_tr_content.html').read_text()
for kind in ('Setup','Hold'):
 m=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
 if not m or int(m[1]):raise RuntimeError(f'{kind} timing not clean')
log=(band/'evidence/band_build.log').read_text(encoding='utf-8-sig',errors='replace')
if 'logical loop' in log or 'ERROR' in log or 'Bitstream generation completed' not in log:raise RuntimeError('Build log is not clean')
release=band/'release';release.mkdir(exist_ok=True)
shutil.copy2(pnr/'starcluster_band.fs',release/'starcluster_band.fs')
sources=list((band/'rtl').glob('*'))+[band.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]+list((band.parent/'constraints').glob('*'))
manifest={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'configuration':'32-slot band, 96-second ROM score, PT8211 audition output','setup_violations':0,'hold_violations':0,'bitstream_sha256':hashlib.sha256((release/'starcluster_band.fs').read_bytes()).hexdigest(),'source_sha256':{str(p.relative_to(band.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources if p.is_file()}}
(release/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='source_sha256'},indent=2))
