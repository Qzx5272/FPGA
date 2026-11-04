"""Reuse production UART fixture against experimental singer/DAC engine."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=r/'synth/band';s=b/'experimental/vocoder'
o=b/'evidence/singer_board_protocol';o.mkdir(exist_ok=True)
t=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(t)+os.pathsep+str(t.parent/'lib')+os.pathsep+env['PATH']
top=(b/'rtl/band_top.v').read_text().replace('module band_top(', 'module singer_test_top(').replace('band_board_engine engine(', 'band_singer_board_engine #(.COEFF_FILE("'+(s/'ported/coeffs.mem').as_posix()+'")) engine(').replace('.panic_out());','.panic_out(),.microphone_sample(24\'sd0),.singer_mix(7\'d0),.singer_gate(),.singer_note(),.dac_dropped(),.dac_underruns());')
original=(b/'tests/tb_board.v').read_text()
tb=original.replace('band_top dut(', 'singer_test_top dut(').replace('synth/band/evidence/board_telemetry.hex',(o/'telemetry.hex').as_posix()).replace('$fclose(f);', 'if(dut.engine.dac_dropped!=0)$fatal(1,"DAC dropped frames");\n  $fclose(f);')
(o/'tb.v').write_text(top+'\n'+tb)
files=list((b/'rtl').glob('*.v'))+list((s/'ported').glob('*.sv'))+list((s/'integration').glob('*.sv'))+[s/'ported/singer_note_control.v',s/'integration/audio_pt8211_queue.v']+[r/'synth/rtl'/n for n in ('hq_sine_quarter.v','uart.v','audio_serial.v')]+[o/'tb.v']
hashes={str(f.relative_to(r)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
c=subprocess.run([str(t/'iverilog.exe'),'-g2012','-I',str(b/'rtl'),'-I',str(s/'ported'),'-I',str(r/'synth/rtl'),'-s','tb_board','-o',str(o/'test.vvp')]+list(map(str,files)),env=env,capture_output=True,text=True)
if c.returncode:raise RuntimeError(c.stderr)
p=subprocess.run([str(t/'vvp.exe'),str(o/'test.vvp')],cwd=r,env=env,capture_output=True,text=True,timeout=300)
d=dict(status='passed' if not p.returncode else 'failed',scope='UART production fixture with experimental singer/core/DAC queue, microphone zero; not physical acceptance or singer-specific UART coverage',log=p.stdout+p.stderr,sha256=hashes)
(o/'result.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(d['status'],d['log']);raise SystemExit(p.returncode)
