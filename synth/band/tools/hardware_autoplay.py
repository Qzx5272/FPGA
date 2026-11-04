"""Read-only observation of a freshly loaded autonomous offline export.

No play, note, tempo or volume commands are sent. Closing the serial port proves
independence from host messages, not Flash power-cycle persistence.
"""
import argparse,datetime,hashlib,json,sys,time
from pathlib import Path
import serial
band=Path(__file__).resolve().parents[1];sys.path.insert(0,str(band/'host'))
from protocol import Event,Decoder,status
ap=argparse.ArgumentParser();ap.add_argument('--project',type=Path,required=True)
ap.add_argument('--program-log',type=Path,required=True);ap.add_argument('--port',default='COM12')
ap.add_argument('--release',type=Path,help='Separately audited board-shell release; defaults to project/release')
ap.add_argument('--output',type=Path)
a=ap.parse_args();project=a.project.resolve()
release=a.release.resolve() if a.release else project/'release'
export=json.loads((project/'export_manifest.json').read_text(encoding='utf-8'))
m=json.loads((release/'manifest.json').read_text())
loaded=json.loads((a.program_log/'loaded_manifest.json').read_text())
flash_record_path=a.program_log/'result.json'
flash_record=json.loads(flash_record_path.read_text(encoding='utf-8')) if flash_record_path.exists() else {}
flash_reload=flash_record.get('status')=='flash_verified_reload_returned_pending_uart'
if flash_record and not flash_reload:
    raise RuntimeError('Programming record is not a successful verified Flash reload')
digest=hashlib.sha256((release/'starcluster_band.fs').read_bytes()).hexdigest()
assert digest==m['bitstream_sha256']==loaded['bitstream_sha256'] and export['autoplay']
if flash_reload and flash_record.get('bitstream_sha256')!=digest:raise RuntimeError('Flash record hash mismatch')
assert export['build_id']==m['build_id'], 'Export and programmed build identity differ'
for name,h in export['sources'].items():
    if hashlib.sha256((project/name).read_bytes()).hexdigest()!=h:raise RuntimeError('Export source changed: '+name)
    if a.release and (name.startswith('rtl/') or name.endswith('.mem')):
        frozen=release/'source_snapshot'/Path(name).name
        if m.get('snapshot_sha256',{}).get(frozen.name)!=h or hashlib.sha256(frozen.read_bytes()).hexdigest()!=h:
            raise RuntimeError('Export does not match board release: '+name)
score=json.loads((project/'project.json').read_text(encoding='utf-8'))
duration=score['duration_samples'];tempo=score.get('performance',{}).get('tempo',120)
decoder=Decoder();records=[];raw=bytearray();identity=None;port=None
result=dict(status='running',started=datetime.datetime.now().isoformat(),project=str(project),
    bitstream_sha256=digest,expected_build_id=m['build_id'],program_log=str(a.program_log.resolve()),
    commands_sent=[18,6],records=records,flash_power_cycle_tested=False,
    scope=('Autoplay after verified Flash write and JTAG reload; no physical power cycle' if flash_reload else
           'Autoplay after SRAM configuration and host serial closure, digital telemetry only'))
path=a.output.resolve() if a.output else band/'evidence/hardware_offline_autoplay.json'
if path.exists():raise RuntimeError('Preserve existing autoplay evidence: '+str(path))
path.parent.mkdir(parents=True,exist_ok=True)
result['test_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
path.with_suffix('.driver.txt').write_bytes(Path(__file__).read_bytes())
def save():
    result['bad_crc']=decoder.bad_crc;path.write_text(json.dumps(result,indent=2));path.with_suffix('.raw').write_bytes(raw)
def connect():return serial.Serial(a.port,1000000,timeout=.01,write_timeout=.2)
def poll(kind=6,timeout=3):
    global identity
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        b=Event(kind).encode_uart()
        if port.write(b)!=len(b):raise IOError('Short UART write')
        time.sleep(.02);chunk=port.read(4096);raw.extend(chunk)
        for f in decoder.feed(chunk):
            if f[1]==161:
                identity=dict(build_id=int.from_bytes(f[4:8],'little'),capacity=int.from_bytes(f[8:12],'little'))
                if kind==18:return identity
            elif kind==6 and f[1] in (128,129):
                s=status(f);s['observed_at']=time.monotonic();records.append(s)
                if s['deadline_miss'] or s['rejected'] or s['clips']:raise RuntimeError('Board error counter: '+repr(s))
                return s
    raise RuntimeError('Telemetry timeout')
try:
    port=connect();id_read=poll(18)
    if id_read!=dict(build_id=m['build_id'],capacity=256):raise RuntimeError('Offline build identity mismatch')
    result['identity']=id_read;s=poll()
    if not s['playing'] or not 0<s['song_sample']<duration:raise RuntimeError('No spontaneous score progress observed')
    first=s;result['first_autonomous_sample']=s['song_sample'];save()
    # Deliberately send no packets and close the port for ten seconds.
    port.close();port=None;quiet_start=time.monotonic();time.sleep(10)
    port=connect();s=poll();quiet_elapsed=s['observed_at']-first['observed_at']
    advance=s['song_sample']-first['song_sample'];expected=quiet_elapsed*48000*tempo/120
    if not s['playing'] or not .95*expected<advance<1.05*expected:raise RuntimeError('Autonomous progress failed across serial closure')
    result['closed_port_seconds']=time.monotonic()-quiet_start
    result['closed_port_sample_advance']=advance;save()
    end=time.monotonic()+duration/48000*120/tempo+10;next_report=0;peak=s['voices']
    while time.monotonic()<end:
        s=poll();peak=max(peak,s['voices'])
        if time.monotonic()>=next_report:
            print('Autoplay sample',s['song_sample'],'voices',s['voices'],flush=True);save();next_report=time.monotonic()+15
        if not s['playing']:break
        time.sleep(.04)
    if s['playing'] or s['song_sample']<duration or peak==0:raise RuntimeError('Autonomous score did not finish')
    until=time.monotonic()+3
    while s['voices'] and time.monotonic()<until:s=poll()
    if s['voices'] or decoder.bad_crc:raise RuntimeError('Release/CRC check failed')
    result.update(status='passed',final_sample=s['song_sample'],peak_observed_voices=peak,
        no_host_play_command=True,master_preset=score.get('performance',{}).get('master',96))
except Exception as e:
    result.update(status='failed',error=repr(e));raise
finally:
    if port:port.close()
    result['finished']=datetime.datetime.now().isoformat();save()
print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
