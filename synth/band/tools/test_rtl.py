"""Standalone band RTL regression; no programming and no production mutation."""
import os,subprocess,sys,json,hashlib,datetime,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[3]
band=root/'synth/band';out=band/'evidence';out.mkdir(exist_ok=True)
binary=root/'tmp/oss-cad-suite/bin'
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
report=out/'rtl_tests.json'
for test in (sys.argv[1:] or ['delay','allocator','ownership','partial','pool','renderer','protocol','board','scanner','pads','store','upload','i2s24','cdc','local','workstation','controls','dispatch','telemetry','board_burst']):
    sources=list((band/'rtl').glob('*.v'))+[root/'synth/rtl/hq_sine_quarter.v',root/'synth/rtl/uart.v',root/'synth/rtl/audio_serial.v',band/f'tests/tb_{test}.v']
    dependencies=sources+list((band/'rtl').glob('*.vh'))+[root/'synth/rtl/sine_quarter_init.vh']
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependencies}
    digest=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:12]
    snapshot=band/f'build/test_{test}_{digest}';snapshot.mkdir(exist_ok=True)
    for p in dependencies:shutil.copy2(p,snapshot/p.name)
    target=snapshot/f'{test}.vvp'
    cmd=[str(binary/'iverilog.exe'),'-g2012','-I',str(snapshot),'-s',f'tb_{test}','-o',str(target),*[str(snapshot/p.name) for p in sources]]
    c=subprocess.run(cmd,env=env,capture_output=True,text=True)
    if c.returncode:raise RuntimeError(c.stdout+c.stderr)
    try:r=subprocess.run([str(binary/'vvp.exe'),str(target)],env=env,capture_output=True,text=True,timeout=180)
    except subprocess.TimeoutExpired as e:r=subprocess.CompletedProcess([],124,'FAIL: wall-clock timeout; incomplete simulation','')
    if test=='board' and r.returncode==0:
        sys.path.insert(0,str(band/'host'));from protocol import Decoder
        decoder=Decoder();frames=decoder.feed(bytes.fromhex((out/'board_telemetry.hex').read_text()))
        identity=[p for p in frames if p[1]==161]
        if decoder.bad_crc or not identity or int.from_bytes(identity[-1][8:12],'little')!=256 or int.from_bytes(identity[-1][12:16],'little')!=48000:
            r=subprocess.CompletedProcess([],1,r.stdout+'FAIL UART identity roundtrip','')
        else:r.stdout+='PASS Python decoder verified UART build identity, 256-slot capacity and nominal sample-rate telemetry\n'
    if test in ('telemetry','board_burst') and r.returncode==0:
        sys.path.insert(0,str(band/'host'));from protocol import Decoder
        decoder=Decoder();name='telemetry_burst.hex' if test=='telemetry' else 'board_burst.hex'
        frames=decoder.feed(bytes.fromhex((out/name).read_text()))
        expected=100 if test=='telemetry' else 50
        if decoder.bad_crc or len(frames)!=expected:
            r=subprocess.CompletedProcess([],1,r.stdout+f'FAIL burst telemetry: frames={len(frames)} CRC={decoder.bad_crc}','')
        else:r.stdout+=f'PASS complete burst frames={len(frames)} CRC=0\n'
    print(r.stdout,flush=True)
    logs=json.loads(report.read_text(encoding='utf-8')) if report.exists() else []
    logs=[entry for entry in logs if entry['test']!=test]
    logs.append({'test':test,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'output':r.stdout+r.stderr,'returncode':r.returncode,'sources':hashes,'source_snapshot':str(snapshot)})
    report.write_text(json.dumps(logs,indent=2),encoding='utf-8')
    if r.returncode or 'PASS' not in r.stdout or 'FAIL' in r.stdout:raise RuntimeError('RTL test failed')
