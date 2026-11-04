from pathlib import Path
import re,json,hashlib
from audit_pt8211_onboard import rows
from timing_pulse import require_clean_pulse
from check_stage_clock_report import check
from verify_fs import verify_fs
b=Path('D:/StarclusterBuilds/lcd_probe_20261031');t=(b/'impl/pnr/lcd_probe_tr_content.html').read_text()
for kind in ['Setup','Hold']:
 m=re.search(r'Numbers of\s*'+kind+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)',t,re.S)
 assert m and int(m[1])==0,(kind,m[1] if m else None)
require_clean_pulse(t);check(t,{'core_clk':20.0,'lcd_pixel':40.0,'lcd_forward':40.0})
active=[r[2] for r in rows(t) if len(r)==3 and r[1]=='Actived']
assert all(s.strip() in active for s in (b/'board.sdc').read_text().splitlines() if s.strip())
ptext=(b/'impl/pnr/lcd_probe.pin.html').read_text().split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(ptext) if len(r)>=17 and r[0]!='Port Name'}
expected=json.loads((b/'pins.json').read_text());assert set(pins)==set(expected)
for n,p in expected.items():
 r=pins[n];assert r[2].split('/')[0]==p and r[3]=='Y' and r[7]=='LVCMOS33' and r[16]=='3.3',(n,r)
 assert r[4]==('in' if n=='clk' else 'out')
bit=b/'impl/pnr/lcd_probe.fs';verify_fs(bit)
e=Path(__file__).resolve().parents[1]/'evidence/lcd_ui_20261031';e.mkdir(exist_ok=True)
r={'status':'passed_setup_hold_pulse_pins_constraints','build':str(b),'resolution':[800,480],'clock_MHz':25,
 'external_timing_assumption':'5ns setup / 1ns hold budget relative to inverted forwarded pixel clock; exact panel datasheet not identified',
 'bitstream_sha256':hashlib.sha256(bit.read_bytes()).hexdigest(),'pins':expected,'flash_written':False}
(e/'probe_audit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
