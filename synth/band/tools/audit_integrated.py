"""Fail-closed audit of the integrated image before any hardware programming."""
from pathlib import Path
import argparse,hashlib,json,re
from audit_pt8211_onboard import rows
from timing_pulse import require_clean_pulse
from check_stage_clock_report import check
from verify_fs import verify_fs
p=argparse.ArgumentParser();p.add_argument('--build',required=True);a=p.parse_args();b=Path(a.build)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((b/'manifest.json').read_text())
for n,h in m['source_sha256'].items():assert sha(b/n)==h,('changed source',n)
t=(b/'impl/pnr/integrated_tr_content.html').read_text()
for kind in ('Setup','Hold'):
 match=re.search(r'Numbers of\s*'+kind+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)',t,re.S)
 assert match and int(match[1])==0,(kind,match[1] if match else None)
require_clean_pulse(t);clocks=check(t,{'core_clk':20.0,'lcd_pixel':40.0,'lcd_forward':40.0})
active=[r[2] for r in rows(t) if len(r)==3 and r[1]=='Actived']
missing=[s.strip() for s in (b/'board.sdc').read_text().splitlines() if s.strip() and not s.startswith('#') and s.strip() not in active]
assert not missing,('inactive constraints',missing)
ptext=(b/'impl/pnr/integrated.pin.html').read_text().split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(ptext) if len(r)>=17 and r[0]!='Port Name'}
expected=json.loads((b/'pins.json').read_text());assert set(pins)==set(expected),(set(pins)^set(expected))
for name,info in expected.items():
 r=pins[name]
 assert r[2].split('/')[0]==info['ball'] and r[3]=='Y' and r[7]=='LVCMOS33' and r[16]=='3.3',(name,r)
 assert r[4]==info['direction'] and r[9]==info['pull'],(name,r)
 if info['drive'] is not None:assert r[8]==str(info['drive']),(name,r)
warnings=[line for line in (b/'impl/pnr/integrated.log').read_text().splitlines() if 'WARN' in line]
assert all('PR1014' in w and "'clk_d'" in w for w in warnings),warnings
bit=b/'impl/pnr/integrated.fs';integrity=verify_fs(bit)
result={'status':'passed','build_id':m['build_id'],'features':0x8000307c if m.get('electronic_singer',True) else 0x8000305c,'bitstream_sha256':sha(bit),
 'clocks':clocks,'pins':expected,'integrity':integrity,'warnings':warnings,'flash_written':False,
 'hardware_verified':False,'limitations':['LCD external delay uses prior verified 5ns/1ns assumption']}
(b/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({'status':'passed','pins':len(pins),'bitstream_sha256':sha(bit)},indent=2))
