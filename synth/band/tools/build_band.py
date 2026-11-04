"""Immutable-source build; never attach new sources to an old bitstream."""
from pathlib import Path
import subprocess,json,hashlib,shutil,re,datetime,argparse
from verify_fs import verify_fs
band=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--publish-existing',action='store_true',help='Verify the existing frozen snapshot and publish its completed build without rerunning tools')
args=parser.parse_args()
sources=list((band/'rtl').glob('*'))+[band.parent/'rtl'/n for n in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]+list((band.parent/'constraints').glob('*'))
sources=[p for p in sources if p.is_file()]
hashes={str(p.relative_to(band.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
build=band/f'build/band_{digest}';snapshot=build/'source_snapshot';snapshot.mkdir(parents=True,exist_ok=True)
identity=f"`define BAND_BUILD_ID 32'h{digest[:8]}\n"
if args.publish_existing:
 if json.loads((build/'source_hashes.json').read_text())!=hashes:raise RuntimeError('Source manifest mismatch')
 for p in sources:
  if p.name=='build_identity.vh':continue # Replaced by the digest-derived identity below.
  if (snapshot/p.name).read_bytes()!=p.read_bytes():raise RuntimeError('Frozen snapshot mismatch: '+p.name)
 if (snapshot/'build_identity.vh').read_text()!=identity:raise RuntimeError('Build identity mismatch')
else:
 for p in sources:shutil.copy2(p,snapshot/p.name)
 (snapshot/'build_identity.vh').write_text(identity)
 (build/'source_hashes.json').write_text(json.dumps(hashes,indent=2))
tcl=f'''cd "{build.as_posix()}"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module band_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
'''+''.join(f'add_file "{p.as_posix()}"\n' for p in snapshot.glob('*.v'))+f'''add_file "{(snapshot/'board.cst').as_posix()}"
add_file "{(snapshot/'board.sdc').as_posix()}"
set_option -output_base_name starcluster_band
run all
'''
log=build/'build.log'
if args.publish_existing:
 if (build/'build.tcl').read_text()!=tcl:raise RuntimeError('Build recipe mismatch')
else:
 (build/'build.tcl').write_text(tcl)
 print('Building frozen source '+digest,flush=True)
 with log.open('w') as f:r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=10800)
 if r.returncode:raise RuntimeError('Build failed; '+str(log))
timing=(build/'impl/pnr/starcluster_band_tr_content.html').read_text();record={'configuration':'8 quota banks x 32 note instances; dynamic expression, finite vowels, double-bank event score; PT8211 audition','evidence_level':'PnR only, not board acceptance','build_id':int(digest[:8],16),'source_sha256':hashes,'snapshot_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir() if p.is_file()},'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
for k in ('Setup','Hold'):
 m=re.search('Numbers of '+k+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
 if not m or int(m[1]):raise RuntimeError(k+' timing failed; '+str(build))
 record[k.lower()+'_violations']=0
text=log.read_text(errors='replace')
if 'logical loop' in text or 'ERROR' in text or 'Bitstream generation completed' not in text:raise RuntimeError('Invalid build log')
record['frequencies_from_report']=re.findall(r'\d+\.\d+\(MHz\)',timing)[:2]
release=band/f'release/band_{digest}';release.mkdir(parents=True,exist_ok=True)
record['bitstream_structure']=verify_fs(build/'impl/pnr/starcluster_band.fs')
shutil.copy2(build/'impl/pnr/starcluster_band.fs',release/'starcluster_band.fs')
shutil.copytree(snapshot,release/'source_snapshot',dirs_exist_ok=True)
for suffix in ('rpt.txt','timing_paths','log'):
 shutil.copy2(build/('impl/pnr/starcluster_band.'+suffix),release/('starcluster_band.'+suffix))
shutil.copy2(build/'build.tcl',release/'original_build.tcl')
record['bitstream_sha256']=hashlib.sha256((release/'starcluster_band.fs').read_bytes()).hexdigest()
(release/'manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='source_sha256'},indent=2))
