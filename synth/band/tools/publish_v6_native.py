"""Audit and freeze the V6 known-pin candidate without changing the selector."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,shutil
from audit_pt8211_onboard import check_pins,rows,expected_clocks
from check_stage_clock_report import check
from review_native_reset_paths import review
from reset_buffer_gate import native_reset_report_commands
from timing_pulse import require_clean_pulse
from verify_fs import verify_fs

band=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--build',type=Path,default=Path('D:/StarclusterBuilds/workstation_v6_native_fixed'))
build=ap.parse_args().build
previous=band/'release/pt8211_dvi_81232ed690d3'
evidence=Path('D:/StarclusterDeliveries/workstation_upgrade_20261027')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('board.cst','board.sdc','board_pt8211_controls_top.sv','gowin_dvi_tx.v','gowin_video_clock.v'):
    current=build/name if name.startswith('board.') else build/'rtl'/name
    assert current.read_bytes()==(previous/'source_snapshot'/name).read_bytes(), 'Changed fixed-pin/reset/clock boundary: '+name
text=(build/'impl/pnr/workstation_v6_tr_content.html').read_text(encoding='utf-8')
violations={}
for kind in ('Setup','Hold'):
    m=re.search(r'Numbers of\s*'+kind+r' Violated Endpoints\s*</td>\s*<td[^>]*>\s*(\d+)\s*</td>',text,re.S)
    assert m and int(m[1])==0, 'Missing/failed '+kind+' timing'
    violations[kind.lower()]=int(m[1])
pulses=require_clean_pulse(text)
commands=[s.strip() for s in (build/'board.sdc').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
reports=[c for c in commands if c.startswith('report_timing ')]
assert reports==native_reset_report_commands()
active=[r[2] for r in rows(text) if len(r)==3 and r[1]=='Actived']
assert all(c in active for c in commands if c not in reports), 'Inactive constraint'
clocks=check(text,expected_clocks(sha(build/'rtl/gowin_video_clock.v'),commands))
native=review(text)
assert native['status']=='native_paths_nonnegative_pending_review' and len(native['paths'])==18
for p in native['paths']:
    assert p['launch']=='display_clk:[F]' and p['source']=='workstation/video_output/transmitter/pixel_release_1_s0'
    assert p['buffer_stages']==list(range(1,16))
vg=(build/'impl/gwsynthesis/workstation_v6.vg').read_text()
for n in range(1,17):
    cells=re.findall(r'\bLUT1 reset_buffer_'+str(n)+r'\s*\((.*?)\);',vg,re.S)
    assert len(cells)==1
    assert f'.F(reset_route_{n})' in cells[0] and f'.I0(reset_route_{n-1})' in cells[0]
    assert vg.count(f"defparam reset_buffer_{n}.INIT=2'h1;")==1
assert vg.count('.RESET(reset_route_16)')==3
pins=check_pins((build/'impl/pnr/workstation_v6.pin.html').read_text(encoding='utf-8'),True)
rt=(build/'impl/pnr/workstation_v6.rpt.txt').read_text()
resources={name:int(re.search(r'^\s*'+re.escape(label)+r'\s*\|\s*(\d+)/',rt,re.M)[1])
 for name,label in [('logic','Logic'),('ff','Register'),('cls','CLS'),('ram','BSRAM'),('dsp','DSP')]}
warnings=[line for line in (build/'impl/pnr/workstation_v6.log').read_text().splitlines() if 'WARN' in line]
assert all('PR1014' in w and "'clk_d'" in w for w in warnings), 'Unreviewed routing warning'
audit=dict(status='passed_fixed_pins_and_constraints',physical_pins=pins,active_commands=commands,
 actual_clocks=clocks,physical_resources=resources,pulse_width_paths_checked=len(pulses),
 pulse_width_violations=0,minimum_pulse_slack_ns=min(p['slack_ns'] for p in pulses),
 native_reset_paths=native,routing_warnings=warnings,setup_violations=0,hold_violations=0,
 scope='18 unchanged fixed pins. Native timing prerequisite only; no acoustic/display/cold-start acceptance.')
(evidence/'native_v6_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
fs=build/'impl/pnr/workstation_v6.fs';integrity=verify_fs(fs);digest=sha(fs)
release=band/'release'/('pt8211_dvi_'+digest[:12])
assert not release.exists(), 'Existing release is immutable'
snapshot=release/'source_snapshot';snapshot.mkdir(parents=True)
for p in (build/'rtl').iterdir():
    if p.is_file():shutil.copy2(p,snapshot/p.name)
for p in list(build.glob('*.mem'))+[build/'board.cst',build/'board.sdc']:
    shutil.copy2(p,snapshot/p.name)
shutil.copy2(fs,release/'starcluster_band.fs')
for source,target in [('workstation_v6_tr_content.html','pt8211_onboard_tr_content.html'),
 ('workstation_v6.pin.html','pt8211_onboard.pin.html'),('workstation_v6.rpt.txt','pt8211_onboard.rpt.txt')]:
    shutil.copy2(build/'impl/pnr'/source,release/target)
(release/'fixed_pin_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
tools=release/'audit_tools';tools.mkdir()
for name in ('audit_pt8211_onboard.py','reset_buffer_gate.py','review_native_reset_paths.py','timing_pulse.py','check_stage_clock_report.py'):
    shutil.copy2(band/'tools'/name,tools/name)
manifest=dict(created=datetime.datetime.now().isoformat(),configuration='V6 known-pin PT8211 + DVI + UART + S0/S1/S2; external inputs tied idle',
 evidence_level='Audited candidate; UART board verification pending',hardware_profile='workstation-pt8211-dvi-v1',
 top_module='board_pt8211_controls_top',onboard_controls=True,verilog_standard='sysv2017',build_id=0x20261028,
 feature_flags=0x8000007c,bitstream_sha256=digest,bitstream_integrity=integrity,setup_violations=0,
 hold_violations=0,pulse_width_violations=0,actual_clocks=clocks,integer_output_clock_trial=False,
 pixel_reset_trial=True,physical_resources=resources,source_build=str(build),routing_warnings=warnings,
 audit_tools_sha256={p.name:sha(p) for p in tools.iterdir()},
 snapshot_sha256={p.name:sha(p) for p in snapshot.iterdir()},
 evidence_sha256={p.name:sha(p) for p in release.iterdir() if p.is_file()})
(release/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(release/'READ_ME.txt').write_text('V6 native fixed-pin candidate. PT8211 is not standard I2S.\nExternal DAC, microphone, panel and BLE require separate unpinned expansion candidate.\n',encoding='utf-8')
print(json.dumps(dict(release=release.name,resources=resources,pins=len(pins),native_reset_paths=len(native['paths']),
 setup=0,hold=0,pulse_paths=len(pulses),minimum_pulse_slack_ns=audit['minimum_pulse_slack_ns']),indent=2))
