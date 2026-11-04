"""Generate isolated, traceable 4096/8192 diagnostic builds and timing evidence."""
from pathlib import Path
import subprocess,json,sys,hashlib,shutil,re
band=Path(__file__).resolve().parents[1];root=band.parents[1]
lb=int(sys.argv[1]) if len(sys.argv)>1 else 3
if lb not in (3,4,5,6):raise ValueError('Lane address bits must be 3..6')
ab=int(sys.argv[2]) if len(sys.argv)>2 else 9
if ab not in (9,10):raise ValueError('Lane depth must be 512 or 1024')
lanes=int(sys.argv[3]) if len(sys.argv)>3 else 1<<lb
n=lanes<<ab
if not 0<lanes<=1<<lb or n>=65536:raise ValueError('Invalid lane count or telemetry overflow')
build=band/f'build/diagnostic{n}';build.mkdir(parents=True,exist_ok=True)
snapshot=build/'source_snapshot';snapshot.mkdir(exist_ok=True)
sources=[band/'rtl'/name for name in ('diagnostic_top.v','partial_pool.v','partial_lane.v','partial_ram16.v','event_receiver.v','status_sender.v')]+[band.parent/'rtl'/name for name in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v')]
for p in sources:shutil.copy2(p,snapshot/p.name)
for p in (band.parent/'constraints').iterdir():shutil.copy2(p,snapshot/p.name)
top=snapshot/'diagnostic_top.v';top.write_text(f'`define POOL_LANE_BITS {lb}\n`define POOL_ADDRESS_BITS {ab}\n`define POOL_LANES {lanes}\n'+top.read_text())
ram=snapshot/'partial_ram16.v';ram.write_text('`define GOWIN_PRIMITIVES\n'+ram.read_text())
tcl=f'''cd "{build.as_posix()}"
set_device -name GW5AST-138B GW5AST-LV138FPG676AC1/I0
set_option -top_module diagnostic_top
set_option -verilog_std v2001
set_option -use_cpu_as_gpio 1
'''+''.join(f'add_file "{p.as_posix()}"\n' for p in snapshot.glob('*.v'))+f'''add_file "{(snapshot/'board.cst').as_posix()}"
add_file "{(snapshot/'board.sdc').as_posix()}"
set_option -output_base_name diagnostic{n}
run all
'''
(build/'build.tcl').write_text(tcl)
log=band/f'evidence/diagnostic{n}_build.log'
with log.open('w') as f:r=subprocess.run(['D:/Gowin/Gowin_V1.9.12.03_x64/IDE/bin/gw_sh.exe',str(build/'build.tcl')],stdout=f,stderr=subprocess.STDOUT,timeout=3600)
if r.returncode:raise RuntimeError('Gowin build failed; see '+str(log))
timing=(build/f'impl/pnr/diagnostic{n}_tr_content.html').read_text()
record={'profile':'independent 112-bit partial diagnostic; not full band','partials':n,'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()},'clock_mhz':50}
for k in ('Setup','Hold'):
 m=re.search('Numbers of '+k+r' Violated Endpoints</td>\s*<td>(\d+)</td>',timing)
 if not m or int(m[1]):raise RuntimeError(k+' timing not clean')
 record[k.lower()+'_violations']=int(m[1])
record['frequencies_from_report']=re.findall(r'\d+\.\d+\(MHz\)',timing)[:2]
from verify_fs import verify_fs
record['bitstream_structure']=verify_fs(build/f'impl/pnr/diagnostic{n}.fs')
release=band/f'release/diagnostic{n}';release.mkdir(parents=True,exist_ok=True)
shutil.copy2(build/f'impl/pnr/diagnostic{n}.fs',release/f'diagnostic{n}.fs')
record['bitstream_sha256']=hashlib.sha256((release/f'diagnostic{n}.fs').read_bytes()).hexdigest()
(release/'manifest.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
