"""Check shared export identity, presets and real reset/slew RTL behavior."""
from pathlib import Path
import datetime, hashlib, json, os, subprocess, sys
band = Path(__file__).resolve().parents[1]
root = band.parents[1]
sys.path.insert(0, str(band / 'host'))
from offline_shared import export_shared_project

out = Path('D:/StarclusterBuilds/shared_export') / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out.mkdir(parents=True)
score = json.loads((band / 'assets/confluence.json').read_text(encoding='utf-8'))
score['engine_profile'] = 'singer-v1'
score['format'] = 'starcluster-score-2'
score['performance'] = {'collaboration': False, 'master': 23, 'tempo': 100,
                        'patches': {'7': {'0': 55, '1': 14000, '2': 4, '4': 0,
                                         '5': 7, '6': 12345, '7': 3}, '15': {'0': 61}}}
target = export_shared_project(score, out / 'project', autoplay=True)
manifest = json.loads((target / 'export_manifest.json').read_text(encoding='utf-8'))
assert manifest['voice_allocation'] == 'shared256-central-parameters'
for name, digest in manifest['sources'].items():
    assert hashlib.sha256((target / name).read_bytes()).hexdigest() == digest
core = (target / 'rtl/band_singer_core.sv').read_text()
assert 'central_voice_bank unit' in core and 'voice_bank #(' not in core
assert 'singer_expression<=61;' in core and 'collaboration_enabled<=0;' in core
before = (target / 'export_manifest.json').read_bytes()
try:
    export_shared_project(score, target)
except ValueError:
    pass
else:
    raise AssertionError('Nonempty destination accepted')
assert (target / 'export_manifest.json').read_bytes() == before
tb = out / 'tb.v'
tb.write_text('''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,tick=0,release_valid=0;
wire [943:0] patches;
shared_role_controls dut(clk,rst,tick,1'b0,4'd0,4'd0,14'd0,release_valid,4'd7,patches);
initial begin
 repeat(3)@(negedge clk);rst=0;
 if(dut.expression[7]!=55||dut.target_expression[7]!=55||dut.bend[7]!=218||dut.target_bend[7]!=218||dut.vowel[7]!=4||dut.attack[7]!=1||dut.sustain[7]!=49380||dut.decay[7]!=7||dut.release_rate[7]!=3)$fatal(1,"exported patch reset mismatch");
 if(dut.expression[6]!=128||dut.attack[6]!=256||dut.sustain[6]!=65535||dut.sustain[0]!=0)$fatal(1,"unconfigured role defaults mismatch");
 release_valid=1;@(negedge clk);release_valid=0;tick=1;
 repeat(128)@(negedge clk);tick=0;
 if(dut.expression[7]!=128||dut.bend[7]!=128)$fatal(1,"release targets not restored");
 $display("PASS exported presets, untouched defaults, release slew");$finish;
end
initial begin #100000;$fatal(1,"timeout");end
endmodule
''')
cad = root / 'tmp/oss-cad-suite'
env = dict(os.environ)
env['PATH'] = str(cad / 'bin') + os.pathsep + str(cad / 'lib') + os.pathsep + env['PATH']
compiled = subprocess.run([str(cad / 'bin/iverilog.exe'), '-g2012', '-s', 'tb', '-I',
                          str(target / 'rtl'), '-o', str(out / 'test.vvp'), str(tb),
                          str(target / 'rtl/shared_role_controls.v')], env=env, capture_output=True, text=True)
assert compiled.returncode == 0, compiled.stdout + compiled.stderr
sim = subprocess.run([str(cad / 'bin/vvp.exe'), str(out / 'test.vvp')], env=env, capture_output=True, text=True, timeout=30)
record = dict(status='passed' if sim.returncode == 0 and 'PASS' in sim.stdout else 'failed',
              scope='Generated shared hierarchy source checks, manifest hashes, nonempty guard and isolated real preset/reset/release-slew RTL; no fulltop timing or board claim',
              export=str(target), export_manifest_sha256=hashlib.sha256(before).hexdigest(),
              log=sim.stdout + sim.stderr,
              source_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in [Path(__file__), band / 'host/offline_shared.py', band / 'host/editor.py']})
(out / 'result.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record, indent=2))
if record['status'] != 'passed': raise SystemExit(1)
