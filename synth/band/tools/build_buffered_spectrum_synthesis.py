"""PCM snapshot/Hann/2048-point FFT resource measurement; no bitstream or timing claim."""
from pathlib import Path
import subprocess,hashlib,json,shutil,datetime
b=Path(__file__).resolve().parents[1];s=b/'experimental/audio_visual'
sources=[s/n for n in ('pcm_snapshot.v','pcm_spectrum.v','spectrum_snapshot.v','pcm_spectrum_buffered.v','fft_fixed.v','fft_twiddle_2048.mem','hann_2048.mem')]
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
target=Path('D:/StarclusterBuilds')/('buffered_spectrum2048_'+digest)
if target.exists():raise RuntimeError('Inspect existing build instead of overwriting '+str(target))
target.mkdir()
for p in sources:shutil.copy2(p,target/p.name)
(target/'build.tcl').write_text('''set here [file dirname [file normalize [info script]]]
cd $here
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module pcm_spectrum_buffered
set_option -verilog_std sysv2017
add_file fft_fixed.v
add_file pcm_snapshot.v
add_file pcm_spectrum.v
add_file spectrum_snapshot.v
add_file pcm_spectrum_buffered.v
set_option -output_base_name buffered_spectrum2048
run syn
''')
o=b/'evidence/buffered_spectrum/synthesis';o.mkdir(parents=True,exist_ok=True)
if (o/'result.json').exists():
 previous=json.loads((o/'result.json').read_text());history=o/'history'/Path(previous['build']).name;history.mkdir(parents=True,exist_ok=False)
 for p in o.iterdir():
  if p.is_file():shutil.copy2(p,history/p.name)
record=dict(status='running',scope='PCM snapshot/Hann/2048FFT/frozen display chain synthesis,no integrated timing/board acceptance',sources=hashes,build=str(target),started=datetime.datetime.now().isoformat())
(o/'result.json').write_text(json.dumps(record,indent=2));print(target,flush=True)
with (target/'build.log').open('w') as log:p=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(target/'build.tcl')],stdout=log,stderr=subprocess.STDOUT,timeout=300)
reports=list((target/'impl/gwsynthesis').glob('*syn.rpt.html'))
record.update(status='passed_synthesis_only' if p.returncode==0 and reports else 'failed',returncode=p.returncode,finished=datetime.datetime.now().isoformat())
for report in reports:shutil.copy2(report,o/report.name)
shutil.copy2(target/'build.log',o/'build.log');shutil.copy2(target/'build.tcl',o/'build.tcl')
(o/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
raise SystemExit(0 if record['status']=='passed_synthesis_only' else 1)
