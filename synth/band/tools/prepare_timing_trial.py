"""Create an isolated timing experiment; never edits the accepted band RTL.

The payload registers do not need a stop/reset clock enable: their valid flags
already suppress consumption. Remove only those unnecessary enables, then prove
behavior with existing regression and waveform comparisons before promotion.
"""
from pathlib import Path
import argparse,hashlib,json,shutil
root=Path(__file__).resolve().parents[3];band=root/'synth/band'
ap=argparse.ArgumentParser();ap.add_argument('destination',type=Path);ap.add_argument('--strategy',choices=['payload_enable','clock_routes'],default='payload_enable');a=ap.parse_args()
target=a.destination.resolve()
if target.exists():raise RuntimeError('Use a fresh isolated destination')
candidate=target/'synth/band';candidate.mkdir(parents=True)
for name in ('rtl','host','tests','tools','assets'):
    shutil.copytree(band/name,candidate/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('build','evidence','release'):(candidate/name).mkdir()
shutil.copytree(root/'synth/constraints',target/'synth/constraints')
(target/'synth/rtl').mkdir()
for name in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v'):
    shutil.copy2(root/'synth/rtl'/name,target/'synth/rtl'/name)
p=candidate/'rtl/band_core.v';original=p.read_text();text=original
control='''   applied_control_source<=saved_control_source;applied_control_part<=saved_control_part;
   applied_control_parameter<=saved_control_parameter;applied_control_value<=saved_control_value;
'''
assert text.count(control)==1
text=text.replace(control,'')
anchor=''' always @(posedge clk)begin
  if(rst||halt)begin control_pending<=0;accepted_control<=0;end'''
assert text.count(anchor)==1
text=text.replace(anchor,''' always @(posedge clk)begin
  // Payload may advance while invalid; halt only clears the validity pipeline.
'''+control+'''  if(rst||halt)begin control_pending<=0;accepted_control<=0;end''')
payload='''   bank_control_part<=effective_control_part;
   bank_control_parameter<=accepted_control?applied_control_parameter:4'd2;
   bank_control_value<=accepted_control?applied_control_value:{7'd0,auto_note};
'''
assert text.count(payload)==1;text=text.replace(payload,'')
anchor=''' always @(posedge clk)begin
  if(rst||halt)bank_control_valid<=0;'''
assert text.count(anchor)==1;text=text.replace(anchor,''' always @(posedge clk)begin
'''+payload+'''  if(rst||halt)bank_control_valid<=0;''')
p.write_text(text)
if a.strategy=='clock_routes':
    # SUG1018-1.7E section2.7 explicitly permits global routing for CE/SR/LOGIC.
    # Preserve every RTL byte. This tests routing only and does not change pins,
    # clock frequency, clocks on the external debugger, or waveform generation.
    shutil.copy2(band/'rtl/band_core.v',p)
    cst=target/'synth/constraints/board.cst'
    with cst.open('a') as f:f.write('\nCLOCK_LOC "engine/rst" BUFG = SR|CE|LOGIC;\nCLOCK_LOC "engine/stop" BUFG = SR|CE|LOGIC;\n')
record=dict(scope='Isolated candidate only, not promoted or programmed',
    original_core_sha256=hashlib.sha256((band/'rtl/band_core.v').read_bytes()).hexdigest(),
    trial_core_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    strategy=a.strategy,
    rationale='Promote reset and stop routing using documented global CE/SR/LOGIC constraints; identical RTL' if a.strategy=='clock_routes' else 'Remove unnecessary halt enables on control payload registers; preserve every validity and panic path',
    required=['RTL regressions','same-score full/fast PCM identity with baseline','50MHz PnR improvement','hardware acceptance before release'])
(target/'EXPERIMENT.json').write_text(json.dumps(record,indent=2));print(target)
