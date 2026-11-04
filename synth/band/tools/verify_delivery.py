"""Re-run meaningful tests using only the packaged source, in a fresh directory."""
from pathlib import Path
import zipfile,sys,datetime,json,os,subprocess,hashlib
root=Path(__file__).resolve().parents[3]
archive=Path(sys.argv[1]).resolve()
validation_root=Path(os.environ.get('STARCLUSTER_VALIDATION_ROOT',str(root/'tmp'))).resolve()
validation_root.mkdir(parents=True,exist_ok=True)
target=validation_root/('delivery_validation_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
target.mkdir()
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if not name.startswith('project/synth/'):continue
        if '/release/' in name or '/evidence/' in name:continue
        destination=(target/name).resolve()
        if target.resolve() not in destination.parents:raise ValueError('Unsafe archive path')
        destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(z.read(name))
project=target/'project';band=project/'synth/band';(band/'evidence').mkdir(exist_ok=True)
env=dict(os.environ);env['QT_QPA_PLATFORM']='offscreen'
host=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(band/'tests'),'-p','test_*.py','-v'],cwd=project,env=env,capture_output=True,text=True)
bin=root/'tmp/oss-cad-suite/bin';env['PATH']=str(bin)+os.pathsep+str(bin.parent/'lib')+os.pathsep+env['PATH']
sources=list((band/'rtl').glob('*.v'))+[project/'synth/rtl'/n for n in ('hq_sine_quarter.v','uart.v','audio_serial.v')]+[band/'tests/tb_board.v']
compiled=subprocess.run([str(bin/'iverilog.exe'),'-g2012','-I',str(band/'rtl'),'-I',str(project/'synth/rtl'),'-s','tb_board','-o',str(target/'board.vvp'),*[str(p) for p in sources]],cwd=project,env=env,capture_output=True,text=True)
simulation=None
if compiled.returncode==0:simulation=subprocess.run([str(bin/'vvp.exe'),str(target/'board.vvp')],cwd=project,env=env,capture_output=True,text=True,timeout=180)
telemetry_ok=False
if simulation is not None and simulation.returncode==0:
    sys.path.insert(0,str(band/'host'))
    from protocol import Decoder
    decoder=Decoder();frames=decoder.feed(bytes.fromhex((band/'evidence/board_telemetry.hex').read_text()))
    telemetry_ok=decoder.bad_crc==0 and any(f[1]==161 and int.from_bytes(f[8:12],'little')==256 for f in frames)
passed=host.returncode==0 and compiled.returncode==0 and simulation is not None and simulation.returncode==0 and 'PASS' in simulation.stdout and telemetry_ok
record=dict(status='passed' if passed else 'failed',archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),extracted_project=str(project),telemetry_crc_and_capacity_verified=telemetry_ok,
            host_output=host.stdout+host.stderr,compile_output=compiled.stdout+compiled.stderr,board_output=simulation.stdout+simulation.stderr if simulation else 'not run',
            external_tools='Existing Python dependencies and OSS CAD executables; project source exclusively from archive')
sidecar=archive.parent/('压缩包源码复现校验.json' if archive.name=='星群V5_完整源码与验证工程.zip' else archive.stem+'_源码复现校验.json')
sidecar.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
if not passed:raise SystemExit(1)
