"""Audit the actual RGB LCD+audio candidate; no HDMI reset exceptions apply."""
from pathlib import Path
import re,json,hashlib,argparse
from audit_pt8211_onboard import rows
from timing_pulse import require_clean_pulse
from check_stage_clock_report import check
from verify_fs import verify_fs
ap=argparse.ArgumentParser();ap.add_argument('--build',default='D:/StarclusterBuilds/lcd_ui_20261031_a');ap.add_argument('--evidence',default='lcd_ui_20261031');a=ap.parse_args()
b=Path(a.build);record=json.loads((b/'candidate.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n,h in record['sources'].items():assert sha(b/n)==h,n
if 'netlist_sha256' in record:assert sha(b/'impl/gwsynthesis/phone_uart.vg')==record['netlist_sha256']
t=(b/'impl/pnr/phone_uart_tr_content.html').read_text()
for kind in ['Setup','Hold']:
 m=re.search(r'Numbers of\s*'+kind+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)',t,re.S);assert m and int(m[1])==0,(kind,m[1] if m else None)
require_clean_pulse(t);clocks=check(t,{'core_clk':20.0,'lcd_pixel':40.0,'lcd_forward':40.0})
active=[r[2] for r in rows(t) if len(r)==3 and r[1]=='Actived']
assert all(s.strip() in active for s in (b/'board.sdc').read_text().splitlines() if s.strip())
ptext=(b/'impl/pnr/phone_uart.pin.html').read_text().split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(ptext) if len(r)>=17 and r[0]!='Port Name'}
expected=json.loads((b/'pins.json').read_text());assert set(pins)==set(expected) and len(pins)==35
inputs={'clk','uart_rx_pin','ble_rx','key_play_n','key_stop_n','key_panic_n'}
for n,p in expected.items():
 r=pins[n];assert r[2].split('/')[0]==p and r[3]=='Y' and r[7]=='LVCMOS33' and r[16]=='3.3',(n,r)
 assert r[4]==('in' if n in inputs else 'out')
 assert r[9]==('UP' if n in inputs-{'clk'} else 'NONE')
 if n not in inputs:assert r[8]=='8'
warnings=[line for line in (b/'impl/pnr/phone_uart.log').read_text().splitlines() if 'WARN' in line]
assert all('PR1014' in w and "'clk_d'" in w for w in warnings),warnings
bit=b/'impl/pnr/phone_uart.fs';integrity=verify_fs(bit)
e=Path(__file__).resolve().parents[1]/'evidence'/a.evidence;e.mkdir(exist_ok=True)
r={'status':'passed_setup_hold_pulse_pins_constraints_sources','build':str(b),'build_id':record['build_id'],'features':record['features'],
 'resolution':[800,480],'clock_MHz':25,'clocks':clocks,
 'external_timing_assumption':'5ns setup / 1ns hold budget relative to inverted forwarded pixel clock; physical color-bar geometry verified, panel datasheet unidentified',
 'bitstream_sha256':sha(bit),'pins':expected,'integrity':integrity,'routing_warnings':warnings,'flash_written':False}
(e/'fpga_audit.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
