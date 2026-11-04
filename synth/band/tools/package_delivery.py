"""Deliver complete project source plus exact released sources and bounded evidence.
Does not include vendor executables, working build databases or private environments.
"""
from pathlib import Path
import zipfile,json,hashlib,datetime,argparse,subprocess,sys
ap=argparse.ArgumentParser();ap.add_argument('--archive-name',default='星群V5_完整源码与验证工程.zip');ap.add_argument('--output-dir',type=Path);args=ap.parse_args()
if Path(args.archive_name).name!=args.archive_name or not args.archive_name.endswith('.zip'):ap.error('archive-name must be a local .zip filename')
root=Path(__file__).resolve().parents[3];band=root/'synth/band';out=root/'output/final_workstation_20261022';out.mkdir(parents=True,exist_ok=True)
# Reconcile hashes at packaging time. A historical green JSON must not certify
# edited host/RTL sources merely because it is still present on disk.
check=subprocess.run([sys.executable,str(band/'tools/software_acceptance.py'),'--require-pass'],capture_output=True,text=True)
if check.returncode:raise RuntimeError('Current source acceptance failed; refresh only stale evidence before packaging:\n'+check.stdout+check.stderr)
acceptance=json.loads((band/'evidence/software_acceptance.json').read_text())
if acceptance['status']!='passed':raise RuntimeError('Current software acceptance is not complete; do not publish a finished package')
files=set()
files.add(root/'synth/tools/load_flash.ps1')
files.add(root/'synth/tools/load_sram.ps1')
files.add(root/'加载FPGA临时程序.cmd')
files.add(root/'启动星群演奏台.cmd')
files.add(root/'烧录FPGA开机程序.cmd')
for folder in ('rtl','host','tests','tools','assets','reference','experimental'):
 for p in (band/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo','.vvp','.vcd','.fst'):files.add(p)
for p in band.iterdir():
 if p.is_file() and p.suffix.lower() in ('.md','.txt','.json','.ps1','.tcl','.sdc','.cst'):files.add(p)
for name in ('hq_sine_quarter.v','sine_quarter_init.vh','uart.v','audio_serial.v'):files.add(root/'synth/rtl'/name)
files.update(p for p in (root/'synth/constraints').iterdir() if p.is_file())
for p in (band/'release').rglob('*'):
 if p.is_file() and p.parent!=band/'release':files.add(p)
# Include every JSON/log report, plus the current complete song and latest timbre
# audition; large generated PCM and FFT sample streams remain reproducible outputs.
files.update(p for p in (band/'evidence').rglob('*') if p.is_file() and p.suffix.lower() in ('.json','.log','.html','.timing_paths','.txt','.raw','.hex'))
# Preserve exact reviewed timing/pin constraints, including failed trials.
files.update(p for p in (band/'evidence').rglob('*') if p.is_file() and p.suffix in ('.sdc','.cst','.tcl'))
files.update(p for p in (band/'evidence/ui').glob('*.png'))
files.update(p for p in (band/'evidence/diagnostic43008').rglob('*') if p.is_file() and p.suffix in ('.v','.vh','.cpp','.tcl'))
files.update(p for p in (band/'evidence/singer_schedule').glob('*.sv') if p.is_file())
files.update(p for p in (band/'evidence/audio_pt8211_jitter').glob('*.v') if p.is_file())
files.update(p for p in (band/'evidence/microphone_capture').glob('*.v') if p.is_file())
files.update(p for p in (band/'evidence/stage_top_chain').glob('*.v') if p.is_file())
files.update(p for p in (band/'evidence/visual_stage_chain').glob('*.v') if p.is_file())
files.update(p for p in (band/'evidence/spectrum_stage_chain').glob('*.v') if p.is_file())
files.update(p for p in (band/'evidence/stage_pad').glob('*.v') if p.is_file())
for fixture in ('buffered_stage_chain','workstation_chain','i2s_stage_chain','workstation_offline','audio_clock_watchdog','i2s24_queue','buffered_spectrum','spectrum_snapshot'):
 files.update(p for p in (band/'evidence'/fixture).glob('tb.v') if p.is_file())
for fixture in ('workstation_render','workstation_load'):
 files.update(p for p in (band/'evidence'/fixture).rglob('*') if p.is_file() and p.suffix in ('.v','.sv','.cpp'))
for fixture in ('coefficient_rom_netlist','vocoder_netlist','stage_pad_netlist','stage_pad_synthesis','stage_export_calibration','stage_pad_candidate','stage_pad_calram','workstation_chain_calram','stage_pad_serialdirty','workstation_chain_serialdirty','spectrum_bars','spectrum_bars_synthesis','pcm_spectrum_display','pcm_spectrum_display_synthesis','pcm_video','pcm_video_synthesis','dvi_symbols','gowin_dvi_tx','gowin_dvi_tx_synthesis','gowin_video_clock','gowin_dvi_clocked','gowin_dvi_output_synthesis','pcm_snapshot_before_domain_reset','spectrum_snapshot_before_domain_reset','workstation_dvi','workstation_dvi_load','vocoder_fanout','vocoder_coeffmux','workstation_pt8211_dvi','workstation_pt8211_dvi_load','pt8211_onboard_synthesis'):
 files.update(p for p in (band/'evidence'/fixture).rglob('*') if p.is_file() and p.suffix in ('.v','.sv','.vg','.mem','.tcl'))
for fixture in ('vocoder_filterbank','vocoder_core','filterbank_four_engines','vocoder_four_engines','vocoder_four_diagnosis','shared_singer_core','four_engine_workstation','portable_vocoder_replay','cached_lead','cached_lead_workstation','reset_buffer_trial','buffered_reset_workstation','reset_buffer_gate','native_reset_review_checks','vision_control','resource_comparison','ensemble_cleanup'):
 files.update(p for p in (band/'evidence'/fixture).rglob('*') if p.is_file() and p.suffix in ('.v','.sv','.py','.mem','.tcl'))
files.update(p for p in (band/'evidence/failed_builds').rglob('*.txt') if p.is_file())
for name in acceptance['details']['current_passed_renders']:
 if any(name.endswith(suffix) for suffix in ('_97s_fast.json','_10s_audition_fast.json','_18s_matrix.json')):
  files.add((band/'evidence'/name).with_suffix('.wav'))
for report in (band/'evidence/singer_render').glob('*.json'):
 render=json.loads(report.read_text())
 if render.get('status')=='passed' and render.get('seconds',0)>=90:
  wav=Path(render['wav']).resolve()
  if not wav.is_relative_to(root.resolve()):raise RuntimeError('Render WAV outside project')
  files.add(wav)
for offline in (out/'offline_confluence_final',out/'offline_verified_20261023',out/'offline_singer_confluence',out/'offline_stage_confluence',out/'offline_stage_selector_confluence',out/'offline_stage_pipelined_confluence',out/'offline_workstation_clockwait_confluence',out/'offline_workstation_load_fixture',out/'offline_workstation_pipeline_confluence',out/'offline_workstation_pipeline_load',out/'offline_workstation_flatrom_confluence',out/'offline_workstation_checked_confluence',out/'offline_workstation_flatrom_load',out/'offline_workstation_coeff22_confluence',out/'offline_workstation_calram_confluence',out/'offline_workstation_calram_load',out/'offline_workstation_serialram_confluence',out/'offline_workstation_serialregs_confluence',out/'offline_workstation_serialregs_load60',out/'offline_workstation_video_confluence',out/'offline_workstation_dvi_confluence',out/'offline_workstation_dvi_compact_confluence',out/'offline_workstation_dvi_clockreset_confluence',out/'offline_workstation_dvi_domains_confluence',out/'offline_workstation_dvi_domains_load60',out/'offline_workstation_pt8211_dvi_confluence',out/'offline_workstation_pt8211_dvi_load60'):
 if not offline.exists():continue
 for folder in ('rtl','constraints','release','licenses'):
  files.update(p for p in (offline/folder).rglob('*') if p.is_file())
 files.update(p for p in offline.iterdir() if p.is_file() and p.suffix in ('.json','.py','.tcl','.txt','.mem'))
# Historical whole-top audition carries its explicit version/scope sidecar.
for offline in (out/'offline_workstation_pt8211_reset_release',out/'offline_workstation_pt8211_coeffmux_4604740fd333',out/'offline_workstation_pt8211_shared_124aa1aed486',out/'offline_workstation_pt8211_shared_c38c151eeea4',out/'offline_workstation_pt8211_central_2c13b385c9c4',out/'offline_workstation_shared_custom_f43876353823',out/'offline_workstation_integer_clock_e80bd58ae490',out/'offline_workstation_pixel_reset_9bc4e8acac49',out/'offline_workstation_pixel_falling_db7d6577285a',out/'offline_workstation_shared_singer_acceptance_20261026',out/'offline_workstation_four_engine_dc2667ea8098'):
 if not offline.exists():continue
 for folder in ('rtl','constraints','release','licenses'):
  files.update(p for p in (offline/folder).rglob('*') if p.is_file())
 files.update(p for p in offline.iterdir() if p.is_file() and p.suffix in ('.json','.py','.tcl','.txt','.mem'))
for name in ('offline_workstation_cached_lead_a027bdf237e2','offline_workstation_reset_buffer_9170e801792b','offline_workstation_reset_buffer_dea9453a599e'):
 offline=out/name
 if not offline.exists():continue
 for folder in ('rtl','constraints','release','licenses'):
  files.update(p for p in (offline/folder).rglob('*') if p.is_file())
 files.update(p for p in offline.iterdir() if p.is_file() and p.suffix in ('.json','.py','.tcl','.txt','.mem'))
for audio in out.glob('*50cf99739a52.wav'):
 files.add(audio);files.add(audio.with_suffix('.json'))
reports=[p for p in out.glob('*.docx') if not p.name.startswith('~$')]
reports.extend(out.glob('*.pdf'))
reports.append(out/'交接报告_验证结果.txt')
reports.extend(p for p in (out/'43008分量_验证补充.txt',out/'43008分量_当前固定节拍验证补充.txt') if p.exists())
reports.extend(p for p in (out/'声码器与资源优化_验证补充.txt',) if p.exists())
reports.extend(p for p in (out/'当前整机交接说明.txt',) if p.exists())
delivery_out=args.output_dir.resolve() if args.output_dir else out
delivery_out.mkdir(parents=True,exist_ok=True)
archive=delivery_out/args.archive_name
if archive.exists():raise RuntimeError('Preserve delivered archive; choose a new archive-name: '+str(archive))
entries=[]
readiness_path=band/'FINAL_READINESS.json'
readiness=json.loads(readiness_path.read_text(encoding='utf-8')) if readiness_path in files else None
if readiness is not None:
 for requirement in readiness['requirements']:
  for evidence in requirement.get('evidence',[]):
   record_path=band/evidence['path']
   if record_path not in files or hashlib.sha256(record_path.read_bytes()).hexdigest()!=evidence['sha256']:
    raise RuntimeError('Readiness evidence changed; restore/review its exact historical record before packaging: '+str(record_path))
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):
  if p==band/'FINAL_READINESS.json':continue
  relative=p.relative_to(root).as_posix();data=p.read_bytes();z.writestr('project/'+relative,data)
  entries.append(dict(path='project/'+relative,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
 # A changed report may have different source/scope, not just a new timestamp.
 # Preserve reviewed references and reject drift, including changes during packing.
 if readiness is not None:
  readiness['archive_evidence_binding']='Exact reviewed evidence hashes preserved; drift rejected rather than rebound'
  for requirement in readiness['requirements']:
   for evidence in requirement.get('evidence',[]):
    reference='project/'+(band.relative_to(root)/evidence['path']).as_posix()
    archived=z.read(reference)
    if hashlib.sha256(archived).hexdigest()!=evidence['sha256']:
     raise RuntimeError('Evidence changed during packaging: '+reference)
  data=json.dumps(readiness,ensure_ascii=False,indent=2).encode('utf-8')
  relative='project/'+readiness_path.relative_to(root).as_posix();z.writestr(relative,data)
  entries.append(dict(path=relative,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
 for p in reports:
  data=p.read_bytes();z.writestr('documents/'+p.name,data);entries.append(dict(path='documents/'+p.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
 manifest=dict(created=datetime.datetime.now().isoformat(),status='engineering snapshot; baseline regression passed; current workstation acceptance remains incomplete',baseline_acceptance=acceptance,file_count=len(entries),files=entries,excluded=['vendor tools and environments','working synthesis databases','reproducible large raw PCM/FFT output'])
 z.writestr('DELIVERY_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
 selector=json.loads((band/'CURRENT_RELEASE.json').read_text(encoding='utf-8'))
 gate_notice=('当前选中固件的发布状态：'+selector.get('release_gate','未提供，必须核验')+'。历史数字板测不能覆盖时序违例；不得绕过下载脚本的时序检查。\n')
 z.writestr('先读这里.txt',(gate_notice+'先读 documents/当前整机交接说明.txt，再读完整方案与 project/synth/band/FINAL_READINESS.json。当前仍为工程候选，非最终验收发布。\nproject 保留全部源码、上位机、音色表、曲谱、测试和构建工具。启动与复现见 project/synth/band/README.txt。\n已修复声码器二维系数ROM的高云综合不一致；旧实验导出带 HARDWARE_BLOCKED 提示，不可用于声码器上板。当前一维ROM候选见交接说明，不能套用旧时序结果。\n普通演出固件以 CURRENT_RELEASE.json 为准。软件、板端数字测试和模拟声音验收不能互相替代；禁止从自动IO探索或未通过时序的build目录任取位流。\n').encode('utf-8'))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for e in entries:
  if hashlib.sha256(z.read(e['path'])).hexdigest()!=e['sha256']:raise RuntimeError('Archive verification failed '+e['path'])
record=dict(archive=str(archive),bytes=archive.stat().st_size,file_count=len(entries),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),all_archived_hashes_verified=True)
checksum=delivery_out/('交付校验.json' if args.archive_name=='星群V5_完整源码与验证工程.zip' else archive.stem+'_校验.json')
checksum.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(record,ensure_ascii=False,indent=2))
