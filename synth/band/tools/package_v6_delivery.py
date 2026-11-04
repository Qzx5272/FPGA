"""Assemble the bounded V6 source, bridge firmware, docs and current evidence."""
from pathlib import Path
import json,shutil,stat

band=Path(__file__).resolve().parents[1]
delivery=Path('D:/StarclusterDeliveries/workstation_upgrade_20261027')
package=delivery/'V6_software_package'
package.mkdir(exist_ok=True)
run_info_path=delivery/'V6_RUN_STATUS.json'
run_info=json.loads(run_info_path.read_text(encoding='utf-8')) if run_info_path.exists() else {}
native_build=Path(run_info.get('native_candidate_build','D:/StarclusterBuilds/workstation_v6_native_fixed'))

def copy(source,relative):
    source=Path(source);target=package/relative;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and not target.stat().st_mode&stat.S_IWRITE:
        if target.read_bytes()==source.read_bytes():return
        raise RuntimeError('Immutable packaged file differs: '+str(target))
    shutil.copy2(source,target)

for name in ('V6_SOFTWARE_DELIVERY_20261027.md','V6_TASK_CLOSURE_20261028.md','HARDWARE_PURCHASE_GUIDE_20261027.md',
             'HARDWARE_INTERFACE.txt','PROTOCOL.txt','IMPLEMENTATION_PLAN.md','README.txt','THIRD_PARTY_NOTICES.txt'):
    copy(band/name,Path('docs')/name)
    copy(band/name,Path('source_tree/synth/band')/name)
copy(Path('output/final_workstation_20261022')/'星群_产品完善与赛项验收实施方案_20261027.md',
     Path('docs')/'星群_产品完善与赛项验收实施方案_20261027.md')
copy(Path('synth/band/tests')/'../reference/官方要求追踪.csv',Path('docs')/'官方要求追踪.csv')

# Keep original relative paths so host offline-export functions remain usable.
source_suffixes={'.py','.ps1','.cmd','.tcl','.v','.sv','.vh','.mem','.cst','.sdc','.cpp','.h','.cjs','.js','.json','.txt','.md','.m','.ini','.html','.csv'}
for relative in ('synth/band/host','synth/band/assets','synth/band/bridges','synth/band/rtl','synth/band/experimental',
                 'synth/band/tools','synth/band/tests','synth/band/reference','synth/rtl','synth/constraints'):
    for p in Path(relative).rglob('*'):
        if not p.is_file() or any(s in p.parts for s in ('build','evidence','__pycache__','.pio')):continue
        if p.suffix in source_suffixes or p.name=='LICENSE':copy(p,Path('source_tree')/p)
copy(band/'requirements-host.txt',Path('source_tree/synth/band/requirements-host.txt'))
for name in ('STATUS.json','FINAL_READINESS.json','CURRENT_RELEASE.json'):
    copy(band/name,Path('docs')/name)
    copy(band/name,Path('source_tree/synth/band')/name)
copy(band/'launch.ps1',Path('source_tree/synth/band/launch.ps1'))
copy(Path('启动星群演奏台.cmd'),Path('source_tree/启动星群演奏台.cmd'))

for p in (band/'host').iterdir():
    if p.is_file() and p.suffix in ('.py','.json'):
        copy(p,Path('host')/p.name)
for p in (band/'assets').glob('*.json'):copy(p,Path('assets')/p.name)
for relative in (Path('esp32c3/platformio.ini'),Path('esp32c3/src/main.cpp'),
                 Path('usb_host/platformio.ini'),Path('usb_host/src/main.cpp'),
                 Path('common/event_wire.h'),Path('phone/index.html'),Path('phone/controller.js'),Path('README.md')):
    copy(band/'bridges'/relative,Path('bridges')/relative)
copy(band/'bridges/esp32c3/.pio/build/esp32-c3-supermini/firmware.bin',Path('bridges/bin/esp32c3-firmware.bin'))
copy(band/'bridges/usb_host/.pio/build/teensy41/firmware.hex',Path('bridges/bin/teensy41-firmware.hex'))
for relative in (Path('experimental/workstation_v6_native'),Path('experimental/panel_v6')):
    for p in (band/relative).iterdir():
        if p.is_file():copy(p,Path('rtl')/relative.name/p.name)
for role,build in (('native_candidate',native_build),
                   ('expansion_candidate',Path('D:/StarclusterBuilds/workstation_v6_expansion'))):
    for p in (build/'rtl').iterdir():
        if p.is_file() and p.suffix in ('.v','.sv','.vh','.mem'):
            copy(p,Path('rtl')/role/p.name)
    for p in build.glob('*.mem'):copy(p,Path('rtl')/role/p.name)
    for name in ('board.cst','board.sdc','build.tcl'):
        p=build/name
        if p.exists():copy(p,Path('rtl')/role/name)
    if role=='native_candidate':
        tcl=(build/'build.tcl').read_text().replace('add_file impl/gwsynthesis/workstation_v6.vg',
            'foreach f [glob rtl/*.v rtl/*.sv] {add_file $f}').replace('run pnr','run all')
        (package/'rtl'/role/'rebuild_all.tcl').write_text(tcl)
for p in (band/'tests').glob('*v6.sv'):
    copy(p,Path('rtl/tests')/p.name)
for name in ('prepare_v6_native_fixed.py','verify_v6_native_fixed.py','publish_v6_native.py',
             'prepare_v6_expansion.py','verify_v6_expansion.py','load_flash.py','load_sram.ps1',
             'mute_after_v6_identity.py'):
    p=band/'tools'/name
    if p.exists():copy(p,Path('tools')/name)
for source,target in ((Path('D:/StarclusterBuilds/v6_native_regression/result.json'),Path('evidence/native_regression.json')),
                      (Path('D:/StarclusterBuilds/c3_behavior/result.json'),Path('evidence/c3_behavior.json')),
                      (Path('D:/StarclusterBuilds/teensy_behavior/result.json'),Path('evidence/teensy_behavior.json')),
                      (Path('D:/StarclusterBuilds/v6_compact16_export/result.json'),Path('evidence/compact16_export.json')),
                      (Path('D:/StarclusterBuilds/v6_compact16_export/impl/gwsynthesis/workstation_v6_export_syn.rpt.html'),Path('evidence/compact16_synthesis_report.html')),
                      (Path('D:/StarclusterBuilds/v6_usb16_export/result.json'),Path('evidence/usb16_export.json')),
                      (Path('D:/StarclusterBuilds/v6_export_scene_verified/elaboration_result.json'),Path('evidence/custom_export_elaboration.json')),
                      (Path('D:/StarclusterBuilds/workstation_v6_expansion/latest_results.json'),Path('evidence/expansion_regression.json')),
                      (Path('D:/StarclusterBuilds/workstation_v6_expansion/impl/gwsynthesis/workstation_v6_expansion_syn.rpt.html'),Path('evidence/expansion_synthesis_report.html')),
                      (delivery/'host_tests_final.log',Path('evidence/host_tests.log')),
                      (Path('D:/StarclusterBuilds/esp32c3_compile_final.log'),Path('evidence/esp32c3_build.log')),
                      (Path('D:/StarclusterBuilds/teensy_compile.log'),Path('evidence/teensy41_build.log'))):
    if source.exists():copy(source,target)
if (delivery/'phone_controller_test.json').exists():
    copy(delivery/'phone_controller_test.json',Path('evidence/phone_controller_test.json'))
if (delivery/'package_smoke.json').exists():
    copy(delivery/'package_smoke.json',Path('evidence/package_smoke.json'))
for p in (delivery/'screenshots').glob('*.png'):copy(p,Path('screenshots')/p.name)
for folder in ('timbre_auditions','pool32_auditions'):
    for p in (delivery/folder).iterdir():
        if p.is_file() and (p.suffix=='.wav' or p.name=='results.json'):
            copy(p,Path('evidence/algorithm_auditions')/folder/p.name)
for name,relative in (('VOXOS_MIT_LICENSE.txt','upstream/LICENSE'),('VOXOS_PROVENANCE.json','PROVENANCE.json')):
    p=band/'experimental/vocoder'/relative
    if p.exists():copy(p,Path('rtl/licenses')/name)

manifest={
    'status':'source_and_bridge_package_ready_native_pnr_pending',
    'stable_board_release':'pt8211_dvi_81232ed690d3',
    'native_candidate_build':'D:/StarclusterBuilds/workstation_v6_native_fixed',
    'expansion_candidate_build':'D:/StarclusterBuilds/workstation_v6_expansion',
    'board_programming':'No V6 update performed by this packaging step',
    'scope':'Source, precompiled bridge firmware, reports and screenshots; no unpinned expansion image',
}
run_status=delivery/'V6_RUN_STATUS.json'
if run_status.exists():
    manifest.update(json.loads(run_status.read_text(encoding='utf-8')))
    copy(run_status,Path('evidence/V6_RUN_STATUS.json'))
    for field in ('native_audit','sram_hardware_evidence','host_hardware_evidence','flash_evidence','post_reload_evidence','gui_evidence'):
        evidence_path=manifest.get(field)
        if evidence_path and Path(evidence_path).exists():copy(evidence_path,Path('evidence')/Path(evidence_path).name)
    # Keep failed and successful vendor logs in separate directories, so a
    # second result.json cannot silently replace the first attempt's evidence.
    for label,field in (('flash_initial_failure','flash_initial_failure'),('flash_final','flash_evidence'),('sram_load','sram_load_log')):
        evidence_path=manifest.get(field)
        if evidence_path:
            path=Path(evidence_path)
            folder=path if path.is_dir() else path.parent
            if folder.exists():
                for p in folder.iterdir():
                    if p.is_file() and p.suffix in ('.txt','.json'):
                        copy(p,Path('evidence/programming')/label/p.name)
    selected=manifest.get('selected_release',manifest['stable_board_release'])
    release=band/'release'/selected
    if release.exists():
        for p in release.rglob('*'):
            if p.is_file():
                copy(p,Path('selected_release')/selected/p.relative_to(release))
                copy(p,Path('source_tree/synth/band/release')/selected/p.relative_to(release))
    manifest['board_programming']=manifest.get('board_result',manifest['board_programming'])
(package/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(package/'README.md').write_text('''# Starcluster V6 software bundle\n\nRead `docs/V6_SOFTWARE_DELIVERY_20261027.md` first, then the hardware power/wiring guide. `host/` and `assets/` are the V6 upper-computer source and event-score assets. ESP32-C3 and Teensy binaries are under `bridges/bin/`; source and phone page are beside them. `rtl/` holds the unpinned experiment sources, not a download package.\n\nThe board currently keeps the previously accepted, fixed-pin PT8211 release. The timing-repair native candidate has not cleared PnR yet. Do not load the extension into the FPGA: it has no reviewed expansion pin constraints. Evidence files state their software, synthesis, or hardware scope.\n''',encoding='utf-8')
print(json.dumps({'package':str(package),'status':manifest['status'],'screenshots':len(list((package/'screenshots').glob('*.png')))},indent=2))
if run_status.exists():
    (package/'README.md').write_text('''# Starcluster V6 software bundle

Read `docs/V6_SOFTWARE_DELIVERY_20261027.md` for scope and `manifest.json` for the actual final board outcome. The matching frozen release is under `selected_release/`; full source with original relative layout is under `source_tree/`. The V6 expansion export keeps instrument, pan, mixer, effects, calibration and three-song ROM settings. Bridge firmware and phone controls are under `bridges/`.

The fixed-pin PT8211 board and the unpinned I2S/panel expansion are different configurations. Never program the unpinned expansion sources. Physical audio, external panel, microphone, Bluetooth and USB-pad acceptance remains explicitly separate in the delivery report.
''',encoding='utf-8')
