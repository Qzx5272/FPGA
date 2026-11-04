"""Isolated synthesis experiment; never edits production RTL or programs a board."""
from pathlib import Path
import argparse, datetime, hashlib, json, re, shutil, subprocess

ap = argparse.ArgumentParser()
ap.add_argument('--maxfan', type=int, default=64)
args = ap.parse_args()
if args.maxfan < 1:
    ap.error('maxfan must be positive')
band = Path(__file__).resolve().parents[1]
source = band / 'experimental/vocoder/ported'
names = ('double_biquad.sv', 'filterbank.sv', 'vocoder_mixer.sv', 'vocoder_core.sv', 'coeffs.mem')
original = {name: (source/name).read_bytes() for name in names}
candidate = dict(original)
text = original['filterbank.sv'].decode().replace('\r\n', '\n')
assert text.count('  state_t state;') == 1
text = text.replace('  state_t state;', f'  state_t state /* synthesis syn_maxfan = {args.maxfan} */;')
candidate['filterbank.sv'] = text.encode()
hashes = {name: hashlib.sha256(data).hexdigest() for name, data in candidate.items()}
digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
build = Path('D:/StarclusterBuilds')/('vocoder_fanout_syn_'+digest)
out = band/'evidence/vocoder_fanout'/digest
if build.exists() or out.exists():
    raise RuntimeError('Existing experiment must be inspected, not overwritten: '+str(build))
(build/'rtl').mkdir(parents=True)
out.mkdir(parents=True)
for name, data in candidate.items():
    (build/('coeffs.mem' if name.endswith('.mem') else 'rtl/'+name)).write_bytes(data)
    (out/name).write_bytes(data)
(build/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module vocoder_core
set_option -verilog_std sysv2017
set_option -use_cpu_as_gpio 1
foreach f [glob rtl/*.sv] {add_file $f}
set_option -output_base_name vocoder_core
run syn
''')
record = dict(status='running', build=str(build), started=datetime.datetime.now().isoformat(),
              sources=hashes, baseline_sources={n:hashlib.sha256(d).hexdigest() for n,d in original.items()},
              maxfan=args.maxfan, scope='Isolated synthesis only; attribute effectiveness must be measured. No numerical, fulltop routing, physical or production acceptance.',
              reference='Gowin SUG550-2.4E section5.11: syn_maxfan signal attribute; excludes clock/CE/reset/set.')
report = out/'result.json'
report.write_text(json.dumps(record, indent=2))
print(build, flush=True)
try:
    with (build/'build.log').open('w') as log:
        run = subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')], stdout=log, stderr=subprocess.STDOUT, timeout=600)
    log = (build/'build.log').read_text(errors='replace')
    if run.returncode or 'ERROR' in log:
        raise RuntimeError('Vendor synthesis failed; inspect preserved log')
    vg = build/'impl/gwsynthesis/vocoder_core.vg'
    net = vg.read_text()
    record['netlist_sha256'] = hashlib.sha256(vg.read_bytes()).hexdigest()
    # Count actual LUT input loads by signal within every synthesized module.
    loads = []
    for module, body in re.findall(r'module\s+(\S+)\s*\((.*?)endmodule', net, re.S):
        counts = {}
        for lut in re.findall(r'\bLUT\w*\s+\S+\s*\((.*?)\);', body, re.S):
            for signal in re.findall(r'\.I\d+\(([^()]+)\)', lut):
                signal = signal.strip()
                if "'" not in signal:
                    counts[signal] = counts.get(signal, 0)+1
        loads.extend(dict(module=module,signal=s,loads=n) for s,n in counts.items() if n>=args.maxfan)
    record.update(status='passed_synthesis_only', high_lut_input_fanout=sorted(loads,key=lambda x:x['loads'],reverse=True)[:40])
except Exception as exc:
    record.update(status='failed',error=str(exc))
    raise
finally:
    for p in (build/'impl/gwsynthesis').glob('*'):
        if p.is_file() and p.suffix in ('.html','.txt'):
            shutil.copy2(p,out/p.name)
    for name in ('build.tcl','build.log'):
        if (build/name).exists(): shutil.copy2(build/name,out/name)
    record['finished'] = datetime.datetime.now().isoformat()
    report.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
