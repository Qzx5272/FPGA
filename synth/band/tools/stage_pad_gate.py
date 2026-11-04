"""Require source-matched pad calibration RAM vendor-netlist evidence."""
from pathlib import Path
import json,hashlib

def require_stage_pad_gate(build):
    b=Path(__file__).resolve().parents[1]
    source=Path(build)/'rtl/stage_pad_frontend.sv'
    expected=hashlib.sha256(source.read_bytes()).hexdigest()
    for report in sorted((b/'evidence/stage_pad_netlist').glob('*/result.json')):
        data=json.loads(report.read_text())
        if data.get('status')!='passed' or data.get('returncode')!=0:continue
        if data.get('source_sha256')!=expected:continue
        if 'PASS all80 calibration RAM addresses and same-edge old-data lookup' not in data.get('log',''):continue
        netlist=report.parent/'stage_pad.vg';bench=report.parent/'tb.v'
        if not netlist.is_file() or hashlib.sha256(netlist.read_bytes()).hexdigest()!=data.get('netlist_sha256'):continue
        if not bench.is_file() or hashlib.sha256(bench.read_bytes()).hexdigest()!=data.get('testbench_sha256'):continue
        generation_proof=None
        if 'generation_changed' in source.read_text():
            # Serial-state RAM needs event/lifecycle evidence as well as calibration.
            for candidate in sorted((b/'evidence/stage_pad_candidate').glob('*/result.json')):
                proof=json.loads(candidate.read_text())
                if proof.get('status')!='passed' or 'PASS200000' not in proof.get('log',''):continue
                if proof.get('sources',{}).get('stage_pad_frontend.sv')!=expected:continue
                if proof.get('vendor_inputs',{}).get('stage_pad.vg')!=data['netlist_sha256']:continue
                bound={**proof['sources'],**proof['vendor_inputs']}
                # Vendor library is identified separately; retain/check every local fixture.
                if any(not (candidate.parent/name).is_file() or hashlib.sha256((candidate.parent/name).read_bytes()).hexdigest()!=h
                       for name,h in bound.items() if name!='prim_sim.v'):continue
                generation_proof=dict(report=str(candidate),sha256=hashlib.sha256(candidate.read_bytes()).hexdigest())
                break
            if generation_proof is None:continue
        return dict(report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),source_sha256=expected,
                    generation_proof=generation_proof,
                    scope='Source-matched isolated pad vendor-netlist calibration/events including80addresses andsame-edge read/write;notfulltop/timing/physical acceptance')
    raise RuntimeError('No source-matched pad netlist evidence covering all80 RAM addresses andread/write collision')
