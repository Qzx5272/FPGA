"""Audit dedicated PT8211+C3 UART candidate before SRAM programming."""
from pathlib import Path
import hashlib,json,re,argparse
from audit_pt8211_onboard import rows,expected_clocks
from check_stage_clock_report import check
from review_native_reset_paths import review
from timing_pulse import require_clean_pulse
from verify_fs import verify_fs
band=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--build',default='D:/StarclusterBuilds/phone_uart_20261031_a');parser.add_argument('--evidence',default='phone_fpga_20261031');args=parser.parse_args()
build=Path(args.build)
base=band/'release/pt8211_dvi_8994dbe5e358'
record=json.loads((build/'candidate.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,h in record['sources'].items():assert sha(build/name)==h,name
text=(build/'impl/pnr/phone_uart_tr_content.html').read_text(encoding='utf-8')
for kind in ('Setup','Hold'):
 m=re.search(r'Numbers of\s*'+kind+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',text,re.S)
 assert m and int(m[1])==0,kind+' timing failed'
pulse=require_clean_pulse(text)
commands=[s.strip() for s in (build/'board.sdc').read_text().splitlines() if s.strip() and not s.lstrip().startswith(('#','//'))]
active=[r[2] for r in rows(text) if len(r)==3 and r[1]=='Actived']
assert all(c in active for c in commands if not c.startswith('report_timing ')), 'Inactive constraint'
clocks=check(text,expected_clocks(sha(build/'rtl/gowin_video_clock.v'),commands))
native=review(text)
assert native['status']=='native_paths_nonnegative_pending_review' and len(native['paths'])==18
for p in native['paths']:
 assert p['launch']=='display_clk:[F]' and p['source']=='workstation/video_output/transmitter/pixel_release_1_s0'
 assert p['buffer_stages']==list(range(1,16))
vg=(build/'impl/gwsynthesis/phone_uart.vg').read_text()
for n in range(1,17):
 cells=re.findall(r'\bLUT1 reset_buffer_'+str(n)+r'\s*\((.*?)\);',vg,re.S)
 assert len(cells)==1 and f'.F(reset_route_{n})' in cells[0] and f'.I0(reset_route_{n-1})' in cells[0]
 assert vg.count(f"defparam reset_buffer_{n}.INIT=2'h1;")==1
assert vg.count('.RESET(reset_route_16)')==3
pintext=(build/'impl/pnr/phone_uart.pin.html').read_text()
section=pintext.split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(section) if len(r)>=17 and r[0]!='Port Name'}
expected=json.loads((base/'fixed_pin_audit.json').read_text())['physical_pins'];expected.update(ble_rx='U16',ble_tx='V16')
assert set(pins)==set(expected) and len(pins)==20
inputs={'clk','uart_rx_pin','ble_rx','key_play_n','key_stop_n','key_panic_n'}
for name,pin in expected.items():
 r=pins[name];assert r[2].split('/')[0]==pin and r[3]=='Y',(name,r)
 assert r[4]==('in' if name in inputs else 'out'),name
 assert r[7]==('LVCMOS33D' if name.startswith('tmds_') else 'LVCMOS33'),name
 assert r[9]==('UP' if name in inputs-{'clk'} else 'NONE') and r[16]=='3.3',name
 if r[4]=='out':assert r[8]=='8',name
warnings=[line for line in (build/'impl/pnr/phone_uart.log').read_text().splitlines() if 'WARN' in line]
assert all('PR1014' in w and "'clk_d'" in w for w in warnings),warnings
bit=build/'impl/pnr/phone_uart.fs';integrity=verify_fs(bit)
out=band/'evidence'/args.evidence;out.mkdir(exist_ok=True)
result={'status':'passed_timing_pins_sources','build':str(build),'build_id':record['build_id'],'features':record['features'],'setup_violations':0,'hold_violations':0,'pulse_width_violations':0,'native_reset_paths':18,'pins':expected,'clocks':clocks,'bitstream_sha256':sha(bit),'integrity':integrity,'routing_warnings':warnings,'programmed':False}
(out/'fpga_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
