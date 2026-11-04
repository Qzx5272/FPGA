"""Check frozen build, all eleven distinct pins and active constraints."""
from pathlib import Path
import argparse,hashlib,json,shutil,stat
from audit_pt8211_onboard import rows
from check_stage_clock_report import clock_periods
ap=argparse.ArgumentParser();ap.add_argument('build',type=Path);args=ap.parse_args()
build=args.build.resolve();root=Path(__file__).resolve().parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=json.loads((build/'result.json').read_text())
assert result['status']=='routed_pending_pin_and_constraint_review'
assert all(result[k+'_violations']==0 for k in ('setup','hold','pulse_width'))
for n,h in result['sources'].items():assert sha(build/n)==h,n
simulation=json.loads((root/'synth/band/evidence/i2s_duplex_20261031/simulation.json').read_text())
assert simulation['status']=='passed'
for name in ('i2s_master_duplex.sv','audio_bringup_top.sv','tone_1k.mem'):
 assert simulation['sources'][str(Path('synth/band/experimental/i2s_duplex')/name)]==result['sources'][name]
pnr=build/'impl/pnr';text=(pnr/'i2s_duplex_tr_content.html').read_text(encoding='utf-8')
clocks=clock_periods(text)
assert set(clocks)=={'core_clk','audio_clk'}
assert abs(clocks['core_clk']-20)<0.005 and abs(clocks['audio_clk']-20*59/29)<0.005
commands=[c.strip() for c in (build/'board.sdc').read_text().splitlines() if c.strip() and not c.lstrip().startswith('#')]
active=[r[2] for r in rows(text) if len(r)==3 and r[1]=='Actived']
assert len(commands)==6 and all(c in active for c in commands)
expected=dict(clk='P16',key_play_n='K16',key_stop_n='F15',key_panic_n='G15',mic_sd='U17',i2s_bck='W21',i2s_ws='Y21',i2s_sd='P21',mic_bck='V19',mic_ws='W19',PA_EN='H17')
assert len(set(expected.values()))==len(expected)
text=(pnr/'i2s_duplex.pin.html').read_text(encoding='utf-8')
section=text.split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
pins={r[0]:r for r in rows(section) if len(r)>=17 and r[0]!='Port Name'}
assert set(pins)==set(expected)
for n,pin in expected.items():
 r=pins[n];assert r[2].split('/')[0]==pin and r[3]=='Y' and r[7]=='LVCMOS33' and r[16]=='3.3'
 assert r[4]==('out' if n in ('i2s_bck','i2s_ws','i2s_sd','mic_bck','mic_ws','PA_EN') else 'in')
 assert r[9]==('UP' if n.startswith('key_') else 'DOWN' if n=='mic_sd' else 'NONE')
bit=pnr/'i2s_duplex.fs';assert bit.is_file()
record=dict(status='digital_build_verified_physical_test_pending',build=str(build),pins=expected,
 clocks_ns=clocks,sample_rate_hz=50e6*29/59/512,setup_violations=0,hold_violations=0,pulse_width_violations=0,
 bitstream_sha256=sha(bit),programmed=False,workstation_integrated=False,
 limitations=['No real microphone/DAC audio measured','70ns input delay is a simulation assumption',
              'PLL physical startup and audio quality pending','Board keys share LCD touch pins',
              'Dedicated tone/monitor image; no UART instrument control or DVI in this image'],
 warnings=[l for l in (build/'build.log').read_text().splitlines() if 'WARN' in l],sources=result['sources'])
dest=root/'output/i2s_audio_20261031';dest.mkdir(exist_ok=True,parents=True)
for n in result['sources']:shutil.copy2(build/n,dest/n)
if (dest/'i2s_duplex.fs').exists():
 (dest/'i2s_duplex.fs').chmod(stat.S_IREAD|stat.S_IWRITE)
shutil.copy2(bit,dest/'i2s_duplex.fs')
for n in ('i2s_duplex_tr_content.html','i2s_duplex.pin.html','i2s_duplex.rpt.txt'):shutil.copy2(pnr/n,dest/n)
shutil.copy2(build/'build.tcl',dest/'build.tcl')
shutil.copy2(root/'synth/band/evidence/i2s_duplex_20261031/simulation.json',dest/'simulation.json')
(dest/'manifest.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
