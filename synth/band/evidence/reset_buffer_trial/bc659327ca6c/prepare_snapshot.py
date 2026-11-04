"""Create an isolated preserved reset-buffer experiment; no timing exceptions."""
from pathlib import Path
import argparse,hashlib,json,shutil
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stages',type=int,default=8);a=ap.parse_args()
if a.stages<2 or a.stages>32 or a.stages%2:ap.error('Use an even stage count2..32')
b=Path(__file__).resolve().parents[1];r=b.parents[1]
base=r/'output/final_workstation_20261022/offline_workstation_pixel_falling_db7d6577285a/rtl'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'gowin_dvi_tx.v')=='1320b5fb12aacb57e89d77db6d84aa32f09c03e8ea98a107af80ca597f8b3576'
s=(base/'gowin_dvi_tx.v').read_text()
chain=' // Experimental reset hold repair. SUG550-2.4E sections5.5/5.9.\n // Propagation must be checked at fast/slow corners after routing; no assumed ns delay.\n'
chain+=' wire reset_route_0 /* synthesis syn_keep=1 syn_dont_touch=1 */;\n assign reset_route_0=!serial_ready;\n'
for n in range(1,a.stages+1):
 chain+=f' wire reset_route_{n} /* synthesis syn_keep=1 syn_dont_touch=1 */;\n LUT1 #(.INIT(2\'h1)) reset_buffer_{n}(.I0(reset_route_{n-1}),.F(reset_route_{n}));\n'
s=s.replace(' genvar lane;',chain+' genvar lane;').replace('.RESET(!serial_ready)',f'.RESET(reset_route_{a.stages})')
digest=hashlib.sha256(s.encode()).hexdigest()[:12]
out=b/'experimental/audio_visual/reset_buffers'/digest;out.mkdir(parents=True,exist_ok=False)
for name in ['starcluster_tmds_encoder.v','dvi_symbols.v','gowin_video_clock.v']:shutil.copy2(base/name,out/name)
(out/'gowin_dvi_tx.v').write_text(s)
e=b/'evidence/reset_buffer_trial'/digest;e.mkdir(parents=True)
record={'status':'prepared_not_validated','source_dir':str(out),'stages':a.stages,'source_sha256':sha(out/'gowin_dvi_tx.v'),'scope':'Even inversion chain preserves reset polarity. Requires preserved physical cells and native recovery/removal checks; no routing, timing or release claim.'}
(e/'preparation.json').write_text(json.dumps(record,indent=2));shutil.copy2(__file__,e/'prepare_snapshot.py');print(json.dumps(record,indent=2))
