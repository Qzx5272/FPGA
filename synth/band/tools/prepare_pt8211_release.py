"""Freeze a timing/pin-audited PT8211 candidate; never program or select it."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

from verify_fs import verify_fs


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('build', type=Path)
args = ap.parse_args()
build = args.build.resolve()
from timing_pulse import require_clean_pulse
require_clean_pulse((build/'impl/pnr/pt8211_onboard_tr_content.html').read_text(encoding='utf-8'))
band = Path(__file__).resolve().parents[1]
evidence = band/'evidence/pt8211_onboard_timing'/build.name.removeprefix('pt8211_onboard_pnr_')
# Re-run the gate against the current files, not just a previous green JSON.
subprocess.run([sys.executable, str(band/'tools/audit_pt8211_onboard.py'), str(build)], check=True,
               stdout=subprocess.DEVNULL)
timing = json.loads((evidence/'result.json').read_text())
audit = json.loads((evidence/'fixed_pin_audit.json').read_text())
source = Path(timing['source'])
synfile = band/'evidence/pt8211_onboard_synthesis'/source.name.removeprefix('pt8211_onboard_syn_')/'result.json'
syn = json.loads(synfile.read_text())
top = syn.get('top_module', 'board_pt8211_dvi_top')
controls = syn.get('onboard_controls', False)
assert top == ('board_pt8211_controls_top' if controls else 'board_pt8211_dvi_top')
assert timing.get('top_module', 'board_pt8211_dvi_top') == top
assert timing.get('onboard_controls', False) == controls
export = Path(syn['export'])
export_manifest = json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
assert export_manifest['hardware_profile'] == 'workstation-pt8211-dvi-v1'
for name, digest in export_manifest['sources'].items():
    assert sha(export/name) == digest, ('Changed export', name)
sources = {}
for name, digest in syn['sources'].items():
    p = build/name if name.endswith('.mem') else build/'rtl'/name
    assert sha(p) == digest, ('Changed routed source snapshot', name)
    if name != top+'.sv':
        relative = name if name.endswith('.mem') else 'rtl/'+name
        assert export_manifest['sources'][relative] == digest, ('Export mismatch', name)
    sources[name] = p
# A resource exploration may reuse the old export, but a changed board shell
# must not masquerade as the already released hardware under the same UART ID.
for prior in (band/'release').glob('*/manifest.json'):
    previous = json.loads(prior.read_text(encoding='utf-8'))
    if previous.get('build_id') == export_manifest['build_id']:
        assert previous.get('top_module') == top, 'Changed board shell requires a distinct build ID'
bitstream = build/'impl/pnr/pt8211_onboard.fs'
integrity = verify_fs(bitstream)
digest = sha(bitstream)
release = band/'release'/('pt8211_dvi_'+digest[:12])
assert not release.exists(), 'Preserve existing release'
snapshot = release/'source_snapshot'
snapshot.mkdir(parents=True)
audit_tools = release/'audit_tools'
audit_tools.mkdir()
for name in ('audit_pt8211_onboard.py','reset_buffer_gate.py','review_native_reset_paths.py',
             'timing_pulse.py','check_stage_clock_report.py'):
    shutil.copy2(band/'tools'/name, audit_tools/name)
for name, p in sources.items():
    shutil.copy2(p, snapshot/name)
for name in ('board.cst', 'board.sdc'):
    shutil.copy2(build/name, snapshot/name)
shutil.copy2(bitstream, release/'starcluster_band.fs')
for p in (evidence/'result.json', evidence/'fixed_pin_audit.json', synfile,
          build/'impl/pnr/pt8211_onboard_tr_content.html', build/'impl/pnr/pt8211_onboard.pin.html',
          build/'impl/pnr/pt8211_onboard.rpt.txt'):
    target = 'synthesis_result.json' if p == synfile else p.name
    shutil.copy2(p, release/target)
manifest = dict(created=datetime.datetime.now().isoformat(),
    configuration='Onboard PT8211 + DVI + UART seats'+(' + S0/S1/S2 controls' if controls else '')+'; microphone/ADC/pedal tied idle',
    evidence_level='Timing and fixed pins audited; board and analog/display acceptance pending',
    hardware_profile='workstation-pt8211-dvi-v1', top_module=top, onboard_controls=controls,
    verilog_standard='sysv2017', build_id=export_manifest['build_id'],
    bitstream_sha256=digest, bitstream_integrity=integrity, setup_violations=0, hold_violations=0,
    pulse_width_violations=0, actual_clocks=audit['actual_clocks'],
    integer_output_clock_trial=timing.get('integer_output_clock_trial', False),
    pixel_reset_trial=timing.get('pixel_reset_trial', False),
    physical_resources=audit['physical_resources'], source_build=str(build),
    audit_tools_sha256={p.name: sha(p) for p in audit_tools.iterdir()},
    routing_warnings=audit.get('routing_warnings', []),
    snapshot_sha256={p.name: sha(p) for p in snapshot.iterdir()},
    evidence_sha256={p.name: sha(p) for p in release.iterdir() if p.is_file()})
(release/'manifest.json').write_text(json.dumps(manifest, indent=2))
(release/'READ_ME.txt').write_text(
    'Candidate only. CURRENT_RELEASE is unchanged. SRAM programming and identity-matched board testing remain.\n'
    'Do not claim microphone/ADC/pedal support in this tied-idle board shell. No Flash acceptance.\n')
print(release)
