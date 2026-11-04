"""Audit isolated PCM5102 candidate before any USB programming."""
from pathlib import Path
import hashlib,json,re
from audit_pt8211_onboard import rows
from check_stage_clock_report import clock_periods
from timing_pulse import require_clean_pulse
b=Path('D:/StarclusterBuilds/pcm5102_song_audio_20261031');p=b/'impl/pnr'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
m=json.loads((b/'candidate.json').read_text())
for n,h in m['sources'].items():assert sha(b/n)==h,n
s=json.loads((b/'serial_test.json').read_text());assert s['status']=='passed'
for n,h in s['sources'].items():assert sha(b/n)==h,n
top=json.loads((b/'top_test.json').read_text());assert top['status']=='passed'
for n,h in top['sources'].items():assert sha(b/n)==h,n
log=(b/'build.log').read_text(errors='replace');assert 'ERROR' not in log
t=(p/'pcm5102_song_tr_content.html').read_text(encoding='utf-8')
for kind in ('Setup','Hold'):
    match=re.search('Numbers of '+kind+r' Violated Endpoints</td>\s*<td>(\d+)</td>',t)
    assert match and int(match[1])==0,kind+' timing failed'
pulse=require_clean_pulse(t);clocks=clock_periods(t)
assert abs(clocks['core_clk']-20)<.005
commands=[c.strip() for c in (b/'board.sdc').read_text().splitlines() if c.strip() and not c.startswith('report_')]
active=[r[2] for r in rows(t) if len(r)==3 and r[1]=='Actived']
assert all(c in active for c in commands),'Inactive constraint'
pintext=(p/'pcm5102_song.pin.html').read_text(encoding='utf-8')
section=pintext.split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(section) if len(r)>=17 and r[0]!='Port Name'}
expected={'clk':'P16','uart_rx_pin':'N16','uart_tx_pin':'P15','HP_BCK':'W21','HP_WS':'Y21','HP_DIN':'P21','PA_EN':'H17',
 'key_play_n':'K16','key_stop_n':'F15','key_panic_n':'G15'}
assert set(pins)==set(expected),(set(pins),set(expected))
for n,ball in expected.items():
    r=pins[n];assert r[2].split('/')[0]==ball,(n,r)
    assert r[7] in ('LVCMOS33','LVCMOS33D') and r[16]=='3.3',(n,r)
    assert r[4]==('in' if n in ('clk','uart_rx_pin','key_play_n','key_stop_n','key_panic_n') else 'out')
m.update(status='audited_pending_board_test',bitstream_sha256=sha(p/'pcm5102_song.fs'),clocks_ns=clocks,
 setup_violations=0,hold_violations=0,pulse_width_violations=0,pins=expected,
 limitations=['Physical song audio pending','Fractional 50MHz clock-enable serializer; not the dedicated audio PLL','Microphone not integrated in song candidate','No Flash write'])
(b/'audit.json').write_text(json.dumps(m,indent=2))
print(json.dumps({k:m[k] for k in ('status','bitstream_sha256','clocks_ns','setup_violations','hold_violations','pulse_width_violations')},indent=2))
