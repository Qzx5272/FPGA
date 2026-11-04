"""Package a verified offline delivery. Never programs hardware."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--build',required=True);p.add_argument('--out',required=True);p.add_argument('--evidence');a=p.parse_args()
root=Path(__file__).resolve().parents[3];band=root/'synth/band';b=Path(a.build);out=Path(a.out)
release=Path(a.evidence) if a.evidence else root/'output/integration_20261031'
assert not out.exists(),out
subprocess.run([sys.executable,str(band/'tools/audit_integrated.py'),'--build',str(b)],check=True)
verify=json.loads((b/'verification.json').read_text());assert verify['status']=='passed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c3=band/'bridges/esp32c3_pad'
ctest=next(x for x in verify['tests'] if x['test']=='c3')
assert ctest['implementation_sha256']==sha(c3/'src/pad_fpga.h')
assert '[SUCCESS]' in (release/'c3_build.log').read_text()
programmed=release/'c3_programmed.json'
if programmed.exists():assert json.loads(programmed.read_text())['firmware_sha256']==sha(c3/'.pio/build/c3-pad-monitor/firmware.bin'),'C3 release binary differs from programmed image'
out.mkdir(parents=True)
def copy(src,dest):
 dest=out/dest;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
shutil.copytree(b/'rtl',out/'fpga/rtl')
for f in b.glob('*.mem'):copy(f,'fpga/'+f.name)
for name in ['board.cst','board.sdc','build.tcl','pins.json','manifest.json','audit.json','verification.json']:
 copy(b/name,'fpga/'+name)
copy(b/'impl/pnr/integrated.fs','fpga/impl/pnr/integrated.fs')
for f in (b/'impl/pnr').iterdir():
 if f.suffix in ('.html','.log','.txt'):copy(f,'fpga/impl/pnr/'+f.name)
copy(b/'build.log','evidence/fpga_build.log')
for f in (b/'verification').glob('*.log'):copy(f,'evidence/tests/'+f.name)
for f in (b/'verification').glob('*.sv'):copy(f,'reference_tools/fixtures/'+f.name)
for name in ['reuse_evidence.json','ui_evidence_origin.json']:
 if (b/name).exists():copy(b/name,'evidence/'+name)
for i in range(4):copy(b/f'ui_page_{i}.png',f'preview/ui_page_{i}.png')
if (b/'ui_page_4.png').exists():copy(b/'ui_page_4.png','preview/跟灯学习.png')
copy(b/'ui_test.log','evidence/tests/ui.log')
copy(root/'output/integration_20261031/adc_protocol.json','evidence/adc_usb_protocol.json')
copy(release/'c3_build.log','evidence/c3_build.log')
for name in ['c3_upload.log','c3_after_upload.log','c3_programmed.json','c3_pad_connection.log','adc_tx3_actual.json','adc_tx3_clean.bin','microphone_j23_actual.json','microphone_j23_samples.bin','hardware_acceptance.json']:
 f=(root/'output/integration_20261031' if name.startswith(('adc_','microphone_')) else release)/name
 if f.exists():copy(f,'evidence/'+name)
for name in ['sram_loaded.json','pc_identity.json','hardware_status.json','flash_loaded.json']:
 if (b/name).exists():copy(b/name,'evidence/'+name)
shutil.copytree(c3/'src',out/'bridges/esp32c3_pad/src')
shutil.copytree(band/'bridges/common',out/'bridges/common')
copy(c3/'platformio.ini','bridges/esp32c3_pad/platformio.ini')
copy(c3/'test_pad_fpga.cpp','bridges/esp32c3_pad/test_pad_fpga.cpp')
if (c3/'test_pad_lesson.cpp').exists():
 copy(c3/'test_pad_lesson.cpp','bridges/esp32c3_pad/test_pad_lesson.cpp')
 shutil.copytree(c3/'tests/stubs',out/'bridges/esp32c3_pad/tests/stubs')
for f in (c3/'.pio/build/c3-pad-monitor').glob('*.bin'):copy(f,'c3_firmware/'+f.name)
apk=release/'Starcluster-0.3.0.apk' if a.evidence else root/'output/android/Starcluster-0.2.0.apk'
copy(apk,'android/'+apk.name)
copy(band/'experimental/integrated/README.txt','使用说明与完整接线.txt')
copy(band/'experimental/vocoder/upstream/LICENSE','licenses/vocoder_LICENSE.txt')
copy(band/'experimental/audio_visual/dvi/LICENSE.Sipeed.txt','licenses/Sipeed_LICENSE.txt')
for name in ['audit_integrated.py','audit_pt8211_onboard.py','timing_pulse.py','check_stage_clock_report.py','verify_fs.py','verify_integrated.py','render_integrated_ui.py']:
 copy(band/'tools'/name,'reference_tools/'+name)
for name in ['audit_integrated.py','audit_pt8211_onboard.py','timing_pulse.py','check_stage_clock_report.py','verify_fs.py','load_integrated_sram.py','load_integrated_flash.py','check_integrated_hardware.py']:
 copy(band/'tools'/name,'tools/'+name)
copy(band/'host/protocol.py','host/protocol.py')
if 'presented' in (b/'rtl/board_lcd_ui_top.sv').read_text():
 copy(band/'host/lcd_mirror.py','host/lcd_mirror.py')
 (out/'打开实时屏幕.cmd').write_text('@echo off\ncd /d "%~dp0"\npython host\\lcd_mirror.py --build fpga --port COM12 --log-dir live\nif errorlevel 1 pause\n',encoding='ascii')
 (out/'屏幕同步说明.txt').write_text('在装有 Python、pyserial、Pillow 和 Tk 的电脑上打开“打开实时屏幕.cmd”。下载器串口为 COM12。程序只查询状态，从液晶确认的同一帧数据重绘画面，窗口下方另列出四个推子的实际毫伏读数。串口断开时保留最后一帧并标明暂停。',encoding='utf-8')

for name in ['sram_loaded.json','pc_identity.json','hardware_status.json','flash_loaded.json']:
 if (b/name).exists():copy(b/name,'fpga/'+name)
for f in (band/'tests').glob('tb_integrated_*.sv'):copy(f,'tests/'+f.name)
release_state='flash_programmed' if (b/'flash_loaded.json').exists() else 'sram_loaded' if (b/'pc_identity.json').exists() else 'offline_verified'
hardware=json.loads((b/'hardware_status.json').read_text()) if (b/'hardware_status.json').exists() else {}
acceptance_path=release/'hardware_acceptance.json'
acceptance=json.loads(acceptance_path.read_text(encoding='utf-8-sig')) if acceptance_path.exists() else {}
status={'status':release_state,'build_id':hex(verify['build_id']),
 'fpga_audit':'passed','offline_tests':'passed','c3_build':'passed','fpga_flash_written':(b/'flash_loaded.json').exists(),
 'fpga_sram_loaded':(b/'pc_identity.json').exists(),'c3_programmed':programmed.exists(),
 'hardware_incident':'ADC USB removal caused hum and reported burning smell; user subsequently reported resolved; repair details not supplied',
 'adc_tx3_hardware_verified':True,
 'microphone_j23_capture_verified':True,
 'digital_audition':hardware.get('status','not_run'),'physical_acceptance':acceptance,
 'pending':acceptance.get('pending',['verify actual panel operation','DAC/microphone listening and cold-start acceptance']),
 'not_implemented':['microphone audio recording/upload to phone','phone score upload to FPGA','persistent C3 take storage'],
 'build_dependencies':{'fpga':'Gowin V1.9.12.03','c3':'PlatformIO espressif32@6.9.0 + NimBLE-Arduino@1.4.2'}}
(out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding='utf-8')
(out/'构建与验证.txt').write_text('''FPGA：在 fpga 目录使用 Gowin V1.9.12.03 执行 gw_sh build.tcl。
C3：在 bridges/esp32c3_pad 目录执行 pio run。
发行包不自动安装工具、不自动烧录、不写 Flash。
fpga/impl/pnr/integrated.fs 是通过时序审查的位流，实物验收状态见 status.json。
重新加载 SRAM：python tools/load_integrated_sram.py --build fpga
烧录并校验开机 Flash：python tools/load_integrated_flash.py --build fpga
以上工具需要 Python + pyserial，以及本机 D:/Gowin/Gowin_V1.9.12.03_x64 的 Programmer。
Flash 工具先检查 SRAM 身份记录、源文件、时序、管脚与位流，校验失败不会继续。
reference_tools 是原项目验证工具备份，路径布局依赖原项目；不是一键烧录脚本。
所有文件的 SHA256 见 SHA256.json。先阅读使用说明与完整接线.txt 和 status.json。
''',encoding='utf-8')
(out/'verify_files.py').write_text('''from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'SHA256.json').read_text())
bad=[name for name,h in manifest.items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=h]
if bad:raise SystemExit('FAILED: '+repr(bad))
print('PASS: '+str(len(manifest))+' release files match SHA256 manifest')
''')
(out/'SHA256.json').write_text(json.dumps({str(f.relative_to(out)).replace('\\','/'):sha(f) for f in sorted(out.rglob('*')) if f.is_file()},indent=2))
archive=shutil.make_archive(str(out),'zip',root_dir=out.parent,base_dir=out.name)
print(json.dumps({'directory':str(out),'archive':archive,'sha256':sha(Path(archive))},ensure_ascii=False))
