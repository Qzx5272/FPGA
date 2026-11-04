"""Fail closed on fixed onboard pins, active constraints and frozen timing inputs.

This is a release prerequisite, not analog/display/CDC MTBF acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import html
import json
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(text):
    return [[html.unescape(re.sub('<[^>]*>', '', cell)).strip()
             for cell in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
            for row in re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.S)]


def expected_clocks(clock_sha, commands, integer_output=False):
    known_sha = ('b58db7ac2ef8fbd1942b158513faba8bc7b5fa296f5222e7b5ee0a1a5d328e0a'
                 if integer_output else
                 '9a4636932e77a4ccb38951684d901288dae3e69cf6a91fdd598158060924ecd7')
    if clock_sha != known_sha:
        raise ValueError('Unreviewed PLL source for selected clock profile')
    ratio = '-multiply_by 121 -divide_by 48' if integer_output else '-multiply_by 63 -divide_by 25'
    expected = 'create_generated_clock -name serial_clk -source [get_ports {clk}] '+ratio+' [get_pins {workstation/video_output/video_clocks/pll/CLKOUT0}]'
    if expected not in commands:
        raise ValueError('PLL source and generated serial clock constraint disagree')
    serial = 50*121/48 if integer_output else 126
    return {'core_clk': 20.0, 'serial_clk': 1000/serial, 'display_clk': 5000/serial}


def check_pins(text, onboard_controls=False):
    section = text.split('name="Pinout_by_Port_Name"', 1)[1].split('</table>', 1)[0]
    expected = dict(clk='P16', uart_rx_pin='N16', uart_tx_pin='P15',
                    HP_BCK='E22', HP_WS='F24', HP_DIN='G24', PA_EN='H17',
                    tmds_clk_p='Y22', tmds_clk_n='Y23')
    for lane, pair in enumerate((('AB24', 'AC24'), ('V24', 'W24'), ('AA22', 'AA23'))):
        expected[f'tmds_d_p[{lane}]'], expected[f'tmds_d_n[{lane}]'] = pair
    controls = dict(key_play_n='K16', key_stop_n='F15', key_panic_n='G15') if onboard_controls else {}
    expected.update(controls)
    pin_rows = [r for r in rows(section) if len(r) >= 17 and r[0] != 'Port Name']
    actual = {r[0]: r for r in pin_rows}
    assert len(actual) == len(pin_rows), 'Duplicate port rows'
    assert set(actual) == set(expected), ('Unexpected/missing ports', set(actual) ^ set(expected))
    for name, pin in expected.items():
        r = actual[name]
        assert r[2].split('/')[0] == pin and r[3] == 'Y', (name, 'pin/constraint', r)
        assert r[4] == ('in' if name in ('clk', 'uart_rx_pin') or name in controls else 'out'), (name, 'direction')
        assert r[7] == ('LVCMOS33D' if name.startswith('tmds_') else 'LVCMOS33'), (name, 'IO type')
        assert r[9] == ('UP' if name == 'uart_rx_pin' or name in controls else 'NONE'), (name, 'pull')
        assert r[16] == '3.3', (name, 'bank voltage')
        if r[4] == 'out':
            assert r[8] == '8', (name, 'drive')
        if name.startswith('tmds_'):
            partner = name.replace('_p', '_n') if '_p' in name else name.replace('_n', '_p')
            assert r[1] == partner, (name, 'differential pair')
    assert 'GW5AST-LV138FPG676AC1/I0' in text, 'Wrong target device'
    return expected


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('build', type=Path)
    build = ap.parse_args().build.resolve()
    band = Path(__file__).resolve().parents[1]
    out = band/'evidence/pt8211_onboard_timing'/build.name.removeprefix('pt8211_onboard_pnr_')
    result = json.loads((out/'result.json').read_text())
    controls = result.get('onboard_controls', False)
    pixel_reset = result.get('pixel_reset_trial', False)
    buffered_reset = sha(build/'rtl/gowin_dvi_tx.v') == '07e54af00ed5cb92a59742f1b12728dc01abab5e73902effc813739cae3f547b'
    assert not result.get('reset_min_delay_trial', False), (
        'Experimental reset minimum-delay constraints lack native OSER recovery/removal '
        'coverage proof; zero summary violations are insufficient for release')
    if pixel_reset:
        assert buffered_reset or sha(build/'rtl/gowin_dvi_tx.v') in ('baea99e3f6656b2574af4ab2622bbcb32d1c905513a0861bf292cad4432df796','1320b5fb12aacb57e89d77db6d84aa32f09c03e8ea98a107af80ca597f8b3576'), 'Unreviewed pixel reset source'
    assert not buffered_reset or pixel_reset, 'Buffered reset requires native pixel-reset constraints'
    assert result['status'] == 'passed_timing_pending_pin_audit', 'No clean final timing'
    assert result['setup_violations'] == result['hold_violations'] == 0
    for name in ('build.tcl', 'board.cst', 'board.sdc'):
        assert sha(build/name) == result['inputs'][name], ('Changed input', name)
    vg = build/'impl/gwsynthesis/pt8211_onboard.vg'
    assert sha(vg) == result['frozen_netlist_sha256'], 'Changed netlist'
    timing = build/'impl/pnr/pt8211_onboard_tr_content.html'
    text = timing.read_text(encoding='utf-8')
    from timing_pulse import require_clean_pulse
    pulse_paths = require_clean_pulse(text)
    commands = [s.strip() for s in (build/'board.sdc').read_text().splitlines()
                if s.strip() and not s.lstrip().startswith('#')]
    native_reset = None
    reports = [c for c in commands if c.startswith('report_timing ')]
    if buffered_reset:
        from reset_buffer_gate import check_reset_buffers, native_reset_report_commands
        from review_native_reset_paths import review
        structure = check_reset_buffers(build)
        assert structure and structure['stages'] == 16, 'Missing synthesized reset chain'
        assert reports == native_reset_report_commands(), 'Missing/changed native reset reports'
        native_reset = review(text)
        assert native_reset['status'] == 'native_paths_nonnegative_pending_review', 'Native reset paths missing or negative'
        assert len(native_reset['paths']) == 18, 'Unexpected native reset path coverage'
        for path in native_reset['paths']:
            assert path['launch'] == 'display_clk:[F]', 'Reset launch clock changed'
            assert path['source'] == 'workstation/video_output/transmitter/pixel_release_1_s0', 'Reset launch register changed'
            # Routed mapping exposes fifteen named delay stages. Actual corner timing,
            # not an assumed per-LUT delay, establishes the release prerequisite.
            assert path['buffer_stages'] == list(range(1,16)), 'Routed reset chain changed; re-review physical paths'
        commands = [c for c in commands if not c.startswith('report_timing ')]
    else:
        assert not reports, 'Unreviewed additional timing commands'
    active = [r[2] for r in rows(text) if len(r) == 3 and r[1] == 'Actived']
    assert len(commands) == (14 if controls else 11)-int(pixel_reset) and all(c in active for c in commands), 'Inactive/missing constraints'
    for kind, count in (('create_clock', 1), ('create_generated_clock', 2),
                        ('set_max_delay', 3), ('set_min_delay', 3), ('set_false_path', (5 if controls else 2)-int(pixel_reset))):
        assert sum(c.startswith(kind+' ') for c in commands) == count, kind
    exceptions = [c for c in commands if c.startswith('set_false_path')]
    expected_exceptions = [
        'set_false_path -hold -from [get_clocks {display_clk}] -to [get_regs {workstation/band/analyzer/display_frame/ack1* workstation/band/analyzer/analysis/reset_sync*}]',
        'set_false_path -from [get_clocks {display_clk}] -to [get_pins {workstation/video_output/transmitter/serial_release_0_s0/CLEAR workstation/video_output/transmitter/serial_release_1_s0/CLEAR}]']
    if pixel_reset:
        expected_exceptions.pop()
    if controls:
        for port, endpoint in [('key_play_n','local_inputs.play_button/synchronized_0_s0'),
                               ('key_stop_n','local_inputs.stop_button/synchronized_0_s0'),
                               ('key_panic_n','local_inputs.panic_sync_0_s0')]:
            expected_exceptions.append('set_false_path -from [get_ports {'+port+'}] -to [get_pins {workstation/band/engine/'+endpoint+'/D}]')
    assert exceptions == expected_exceptions
    from check_stage_clock_report import check
    clocks = check(text, expected_clocks(sha(build/'rtl/gowin_video_clock.v'), commands,
                                       result.get('integer_output_clock_trial', False)))
    pinfile = build/'impl/pnr/pt8211_onboard.pin.html'
    pins = check_pins(pinfile.read_text(encoding='utf-8'), controls)
    resource = build/'impl/pnr/pt8211_onboard.rpt.txt'
    rt = resource.read_text()
    resources = {name: int(re.search(r'^\s*'+re.escape(label)+r'\s*\|\s*(\d+)/', rt, re.M)[1])
                 for name, label in [('logic', 'Logic'), ('ff', 'Register'), ('cls', 'CLS'), ('ram', 'BSRAM'), ('dsp', 'DSP')]}
    record = dict(status='passed_fixed_pins_and_constraints', physical_pins=pins,
                  active_commands=commands, actual_clocks=clocks, physical_resources=resources,
                  pulse_width_paths_checked=len(pulse_paths),pulse_width_violations=0,
                  native_reset_paths=native_reset,timing_report_commands=reports,
                  routing_warnings=[line for line in (build/'build.log').read_text().splitlines() if 'WARN' in line],
                  scope=f'{len(pins)} fixed physical pins; no automatic IO. Digital timing prerequisite only; board release, analog, display, cold-start and peripherals remain separate.',
                  sources={str(p.relative_to(build)) if p.is_relative_to(build) else p.name: sha(p)
                           for p in (timing, pinfile, resource, vg, build/'board.cst', build/'board.sdc', build/'build.log', out/'result.json', Path(__file__),
                                     band/'tools/reset_buffer_gate.py', band/'tools/review_native_reset_paths.py',
                                     band/'tools/timing_pulse.py', band/'tools/check_stage_clock_report.py')})
    (out/'fixed_pin_audit.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
