"""Isolated coefficient mux experiment: independent RTL vectors then synthesis."""
from pathlib import Path
import argparse, datetime, hashlib, json, re, shutil, subprocess, os

band = Path(__file__).resolve().parents[1]
source = band / 'experimental/vocoder/ported'
names = ('double_biquad.sv', 'filterbank.sv', 'vocoder_mixer.sv', 'vocoder_core.sv', 'coeffs.mem')
original = {name: (source/name).read_bytes() for name in names}
candidate = dict(original)
text = original['filterbank.sv'].decode().replace('\r\n', '\n')
# The coefficient bank is constant throughout each biquad transaction.
# Select the lowpass row only for ENVELOPE; no coefficient FFs are needed.
text = text.replace('logic signed [31:0] coeffs', 'wire signed [31:0] coeffs')
patterns = [
 '        for(int k=0;k<10;k++) coeffs[j][k]<=0;\n',
 '              for (int j = 0; j < 10; j++) coeffs[i][j] <= COEFFS[i*10+j];\n',
 '              for (int j = 0; j < 10; j++) coeffs[i][j] <= COEFFS[N_FILTERS*10+j];\n']
for pattern, expected in zip(patterns, (1, 2, 1)):
    assert text.count(pattern) == expected
    text = text.replace(pattern, '')
needle = '    for (genvar i = 0; i < N_FILTERS; i++) begin\n'
assert text.count(needle) == 1
text = text.replace(needle, needle + "      for (genvar c=0;c<10;c++) begin : coefficient_select\n        assign coeffs[i][c] = (state == ENVELOPE) ? COEFFS[N_FILTERS*10+c] : COEFFS[i*10+c];\n      end\n")
candidate['filterbank.sv'] = text.encode()
hashes = {name: hashlib.sha256(data).hexdigest() for name, data in candidate.items()}
digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
build = Path('D:/StarclusterBuilds')/('vocoder_coeffmux_syn_'+digest)
out = band/'evidence/vocoder_coeffmux'/digest
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
              change="constant coefficient row selection replaces coefficient holding registers", scope='Isolated synthesis and separately recorded4096sample RTL proof;no vendor-netlist,fulltop routing,physical orproduction acceptance.',
              reference='Original4096sample independent fixed-point vectors;unchanged biquad arithmetic and153cycle schedule.')
report = out/'result.json'
report.write_text(json.dumps(record, indent=2))
print(build, flush=True)
try:
    prior = band/'evidence/vocoder_core'
    reference = json.loads((prior/'result.json').read_text())
    assert reference['status'] == 'passed' and reference['sha256'] == record['baseline_sources']
    shutil.copy2(prior/'vectors.hex',out/'vectors.hex')
    tb = (prior/'tb.sv').read_text()
    tb = re.sub(r'\.COEFF_FILE\("[^"]+"\)', '.COEFF_FILE("coeffs.mem")', tb)
    (out/'tb.sv').write_text(tb)
    binary = band.parents[1]/'tmp/oss-cad-suite/bin'
    env = dict(os.environ)
    env['PATH'] = str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
    with (out/'rtl_compile.log').open('w') as log:
        run = subprocess.run([str(binary/'iverilog.exe'),'-g2012','-s','tb','-o',str(out/'test.vvp'),*[str(build/'rtl'/n) for n in names if n.endswith('.sv')],str(out/'tb.sv')],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert run.returncode==0,'RTL compile failed'
    with (out/'rtl_simulation.log').open('w') as log:
        run = subprocess.run([str(binary/'vvp.exe'),str(out/'test.vvp')],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    rtl_log = (out/'rtl_simulation.log').read_text()
    assert run.returncode==0 and 'PASS full vocoder4096' in rtl_log,rtl_log
    numerical = dict(status='passed',sha256=hashes,scope='4096sample isolated candidate RTL against unchanged independent reference;not vendor netlist orphysical acceptance',log=rtl_log,reference_sha256=hashlib.sha256((prior/'result.json').read_bytes()).hexdigest(),vectors_sha256=hashlib.sha256((out/'vectors.hex').read_bytes()).hexdigest())
    (out/'rtl_result.json').write_text(json.dumps(numerical,indent=2))
    record['rtl_numerical_gate'] = numerical
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
        loads.extend(dict(module=module,signal=s,loads=n) for s,n in counts.items() if n>=64)
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
