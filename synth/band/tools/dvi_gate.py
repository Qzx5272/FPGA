"""Require a source-matched actual band-to-serial-pin simulation before DVI PnR."""
from pathlib import Path
import json,hashlib,re,html

def require_dvi_gate(build):
    b=Path(__file__).resolve().parents[1]
    files=list((build/'rtl').glob('*'))+list(build.glob('*.mem'))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
    driver=b/'tools/test_workstation_dvi.py'
    for report in sorted((b/'evidence/workstation_dvi').glob('*/result.json'),reverse=True):
        data=json.loads(report.read_text());proof=data.get('sources',{})
        if data.get('status')!='passed' or data.get('serial_bits_checked_per_lane',0)<12000 or data.get('colored_input_pixels',0)<=0:continue
        if proof.get(driver.name)!=hashlib.sha256(driver.read_bytes()).hexdigest():continue
        if not all(proof.get(name)==digest for name,digest in hashes.items()):continue
        snapshot=Path(data['build'])
        if not all((snapshot/name).is_file() and hashlib.sha256((snapshot/name).read_bytes()).hexdigest()==digest for name,digest in hashes.items()):continue
        return dict(report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),scope=data['scope'])
    raise RuntimeError('No source-matched full band/PLL/TMDS serial-pin proof; finish test_workstation_dvi.py first')


def require_dvi_clock_gate(build):
    """Bind the actual PLL/serializer RTL to its narrowly scoped boundary PnR."""
    b=Path(__file__).resolve().parents[1]
    names=('dvi_symbols.v','gowin_dvi_output.v','gowin_dvi_tx.v',
           'gowin_video_clock.v','starcluster_tmds_encoder.v')
    expected={n:hashlib.sha256((build/'rtl'/n).read_bytes()).hexdigest() for n in names}
    for report in sorted((b/'evidence/dvi_output_timing').glob('*/result.json'),reverse=True):
        data=json.loads(report.read_text(encoding='utf-8'))
        if data.get('status')!='passed_internal_timing_only':continue
        if data.get('setup_violations')!=0 or data.get('hold_violations')!=0:continue
        source=Path(data['source_build']);snapshot=Path(data['build'])
        if not all((source/n).is_file() and hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in expected.items()):continue
        netlist=snapshot/'impl/gwsynthesis/gowin_dvi_output.vg'
        if not netlist.is_file() or hashlib.sha256(netlist.read_bytes()).hexdigest()!=data['frozen_netlist_sha256']:continue
        synth=b/'evidence/gowin_dvi_output_synthesis'/source.name.removeprefix('gowin_dvi_output_syn_')/'result.json'
        if not synth.is_file():continue
        syn=json.loads(synth.read_text(encoding='utf-8'))
        if syn.get('status')!='passed_synthesis_only' or syn.get('source_hashes')!=expected:continue
        source_netlist=source/'impl/gwsynthesis/gowin_dvi_output.vg'
        if hashlib.sha256(source_netlist.read_bytes()).hexdigest()!=data['frozen_netlist_sha256']:continue
        from check_stage_clock_report import check
        timing=snapshot/'impl/pnr/gowin_dvi_output_tr_content.html'
        clocks=check(timing.read_text(encoding='utf-8'),{'reference_clk':20.0,'serial_clk':1000/126,'pixel_clk':1000/25.2})
        sdc=snapshot/'display.sdc'
        commands=[line.strip() for line in sdc.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
        reset_exception='set_false_path -from [get_clocks {pixel_clk}] -to [get_pins {transmitter/serial_release_0_s0/CLEAR transmitter/serial_release_1_s0/CLEAR}]'
        clocks_only=[line for line in commands if line.startswith(('create_clock ','create_generated_clock '))]
        extras=[line for line in commands if line not in clocks_only]
        if len(clocks_only)!=3 or extras not in ([],[reset_exception]):continue
        active=[]
        for row in re.findall(r'<tr>(.*?)</tr>',timing.read_text(encoding='utf-8'),re.S):
            cells=[html.unescape(re.sub('<[^>]*>','',v)).strip() for v in re.findall(r'<td[^>]*>(.*?)</td>',row,re.S)]
            if len(cells)==3 and cells[1]=='Actived':active.append(cells[2])
        if not all(command in active for command in commands):continue
        return dict(report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
                    synthesis_report_sha256=hashlib.sha256(synth.read_bytes()).hexdigest(),
                    timing_report_sha256=hashlib.sha256(timing.read_bytes()).hexdigest(),
                    sdc_sha256=hashlib.sha256(sdc.read_bytes()).hexdigest(),clocks=clocks,reset_pin_exceptions=extras,
                    scope='Exact-source PLL/serializer boundary internal timing only;no external or full-band acceptance')
    raise RuntimeError('No source-matched zero-violation PLL/serializer boundary timing; validate small DVI boundary first')
