"""Require source-matched post-synthesis evidence before experimental PnR."""
from pathlib import Path
import sys,json,hashlib

def require_vocoder_gate(build,evidence=None):
    band=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(band/'host'))
    from rom_contract import check_vocoder_rom
    build=Path(build);check_vocoder_rom(build/'rtl/filterbank.sv')
    names=('double_biquad.sv','filterbank.sv','vocoder_mixer.sv','vocoder_core.sv','coeffs.mem')
    actual={n:hashlib.sha256((build/('coeffs.mem' if n.endswith('.mem') else 'rtl/'+n)).read_bytes()).hexdigest() for n in names}
    for report in sorted(Path(evidence or band/'evidence/vocoder_netlist').glob('*/result.json')):
        record=json.loads(report.read_text())
        if record.get('status')!='passed' or record.get('returncode')!=0:continue
        if record.get('reference',{}).get('sha256')!=actual:continue
        if 'PASS vendor-netlist320' not in record.get('log',''):continue
        netlist=report.parent/'vocoder_core.vg'
        if not netlist.is_file() or hashlib.sha256(netlist.read_bytes()).hexdigest()!=record.get('netlist_sha256'):continue
        return dict(report=str(report),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),netlist_sha256=record['netlist_sha256'],
                    scope='Matching5vocoder sources andpassed320sample isolated vendor-netlist test;not fulltop equivalence or physical acceptance')
    raise RuntimeError('No source-matched passed320sample vocoder netlist evidence;run test_vocoder_netlist.py before PnR')
