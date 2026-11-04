"""Prepare a portable Gowin project from a release's verified frozen source.

This does not synthesize, program, or promise a byte-identical result across tools.
The rebuilt output must pass timing again before it is eligible for download.
"""
from pathlib import Path
import argparse,json,hashlib,shutil,datetime
ap=argparse.ArgumentParser();ap.add_argument('release',type=Path);ap.add_argument('destination',type=Path)
args=ap.parse_args();release=args.release.resolve();destination=args.destination.resolve()
if destination.exists() and any(destination.iterdir()):raise RuntimeError('Destination must be absent or empty')
m=json.loads((release/'manifest.json').read_text())
snapshot=release/'source_snapshot'
hashes=m.get('snapshot_sha256',m.get('sources',{}))
if not hashes or not snapshot.is_dir():raise RuntimeError('This release has no supported flat source snapshot')
for name,digest in hashes.items():
    source=(snapshot/name).resolve()
    if source.parent!=snapshot or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise RuntimeError('Invalid snapshot '+name)
top=m.get('top_module','diagnostic_top' if release.name.startswith('diagnostic') else 'band_top')
standard=m.get('verilog_standard','v2001')
if top not in ('diagnostic_top','band_top','board_pt8211_dvi_top') or standard not in ('v2001','sysv2017'):
    raise RuntimeError('Unsupported release top/language')
destination.mkdir(parents=True,exist_ok=True)
target=destination/'source';shutil.copytree(snapshot,target)
lines=['cd [file dirname [file normalize [info script]]]','set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0',
       'set_option -top_module '+top,'set_option -verilog_std '+standard,'set_option -use_cpu_as_gpio 1']
lines += ['add_file "source/'+p.name+'"' for p in sorted(list(target.glob('*.v'))+list(target.glob('*.sv')))]
# readmemh paths in the frozen RTL are relative to the build working directory.
for p in target.glob('*.mem'):shutil.copy2(p,destination/p.name)
lines += ['add_file "source/board.cst"','add_file "source/board.sdc"','set_option -output_base_name reproduced','run all']
(destination/'build.tcl').write_text('\n'.join(lines)+'\n')
record=dict(created=datetime.datetime.now().isoformat(),release=release.name,source_manifest_sha256=hashlib.sha256((release/'manifest.json').read_bytes()).hexdigest(),verified_files=len(hashes),top=top,status='prepared only; no synthesis or programming')
(destination/'provenance.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
