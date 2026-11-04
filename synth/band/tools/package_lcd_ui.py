"""Package only an audited LCD candidate and its exact source inputs."""
from pathlib import Path
import hashlib,json,shutil,zipfile
band=Path(__file__).resolve().parents[1];root=band.parents[1]
build=Path('D:/StarclusterBuilds/lcd_ui_20261031_c');e=band/'evidence/lcd_ui_20261031'
audit=json.loads((e/'fpga_audit.json').read_text());record=json.loads((build/'candidate.json').read_text())
bit=build/'impl/pnr/phone_uart.fs';assert hashlib.sha256(bit.read_bytes()).hexdigest()==audit['bitstream_sha256']
out=root/'output/lcd_ui_20261031';out.mkdir(parents=True,exist_ok=True)
target=out/'starcluster_lcd_ui.fs'
if target.exists():assert hashlib.sha256(target.read_bytes()).hexdigest()==audit['bitstream_sha256']
else:shutil.copy2(bit,target)
for name in ['fpga_audit.json','pc_identity.json','progress.json','pixel_test.log','state_test.log','panel_plan_audit.json','ui_preview.png']:
 if (e/name).exists():shutil.copy2(e/name,out/name)
with zipfile.ZipFile(out/'exact_build_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name,h in record['sources'].items():
  p=build/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h;z.write(p,name)
 z.write(build/'candidate.json','candidate.json')
 z.write(build/'impl/gwsynthesis/phone_uart.vg','impl/gwsynthesis/phone_uart.vg')
 portable='\n'.join(line for line in (build/'build.tcl').read_text().splitlines() if not line.startswith('set_option -inc_pnr'))+'\n'
 z.writestr('portable_build.tcl',portable)
 z.writestr('REBUILD.txt','The original build.tcl records the audited build. For an independent netlist rebuild use portable_build.tcl; it does not require the original parent .pr. Reaudit all timing/pins after rebuilding. Supplied .fs is SRAM-only in this delivery.\n')
 for p in list((band/'experimental/hdmi_ui').glob('*'))+list((band/'experimental/lcd_ui').glob('*')):
  if p.suffix in ('.md','.py','.sv','.png'):z.write(p,'validation/'+p.parent.name+'/'+p.name)
shutil.copy2(band/'hardware/wiring_proposal_20261028/面板更新_6旋钮按压_4按键_20261031.md',out/'面板方案.md')
print(out)
