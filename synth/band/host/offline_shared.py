"""Export editable score/presets with the shared instrument pool.

Source export only: every new composition requires its own build and acceptance.
"""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
from offline import replace_once
from offline_pt8211_dvi import export_pt8211_dvi_project


def export_shared_project(score, destination, autoplay=True):
    if score.get('engine_profile') != 'singer-v1':
        raise ValueError('共享乐队导出要求第16轨为电子歌手')
    if any(int(k) in (8,9) for params in score.get('performance',{}).get('patches',{}).values() for k in params):
        raise ValueError('逐声部音色/声像场景请使用V6扩展生成器，不能导出为旧板载工程')
    target = export_pt8211_dvi_project(score, destination, autoplay)
    rtl = target / 'rtl'
    source = Path(__file__).resolve().parents[1] / 'experimental/shared_voices'
    central = source / 'central_parameters'
    for name in ('shared_bank_dispatch.v', 'shared_note_allocator.v', 'shared_band_renderer.v'):
        shutil.copyfile(source / name, rtl / name)
    shutil.copyfile(central / 'central_voice_bank.v', rtl / 'central_voice_bank.v')
    controls = (central / 'shared_role_controls.v').read_text()
    controls = replace_once(controls, ' integer i;', ' `include "offline_patch_defaults.vh"\n integer i;')
    start = controls.index('   expression[i]<=128;')
    end = controls.index('  end else begin', start)
    assignments = {'expression': 0, 'target_expression': 0, 'bend': 1,
                   'target_bend': 1, 'vowel': 2, 'attack': 4, 'sustain': 6,
                   'decay': 5, 'release_rate': 7}
    controls = controls[:start] + '   ' + ''.join(
        f'{name}[i]<=offline_parameter_{parameter}(i);'
        for name, parameter in assignments.items()) + '\n' + controls[end:]
    (rtl / 'shared_role_controls.v').write_text(controls)
    core = (central / 'central_band_singer_core.sv').read_text()
    core = replace_once(core, 'module central_band_singer_core #', 'module band_singer_core #')
    performance = score.get('performance', {})
    patches = {int(k): {int(p): v for p, v in values.items()}
               for k, values in performance.get('patches', {}).items()}
    core = replace_once(core, 'collaboration_enabled<=1;',
                        f"collaboration_enabled<={int(performance.get('collaboration', True))};")
    core = replace_once(core, 'singer_expression<=80;',
                        f"singer_expression<={patches.get(15, {}).get(0, 127)};")
    (rtl / 'band_singer_core.sv').write_text(core)
    # The shared renderer now implements roles8–14. Advertise only in this export.
    engine_path=rtl/'band_stage_pt8211_engine.sv'
    if engine_path.exists():
        engine=engine_path.read_text(encoding='utf-8')
        engine=engine.replace("8000003c", "8000007c")
        engine_path.write_text(engine,encoding='utf-8')
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in sorted(rtl.iterdir())
                                    if p.name != 'build_identity.vh')).hexdigest()
    (rtl / 'build_identity.vh').write_text(f"`define BAND_BUILD_ID 32'h{digest[:8]}\n")
    readme = target / 'READ_ME.txt'
    readme.write_text(readme.read_text(encoding='utf-8') +
        '\n共享版：256个乐器槽动态分配，电子歌手独立；每轨预设在中央参数表复位时载入。'
        '新增曲谱/参数会改变构建身份，不能继承现有发布的时序或实板结论。\n', encoding='utf-8')
    manifest_path = target / 'export_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update(created=datetime.datetime.now().isoformat(), build_id=int(digest[:8], 16),
                    voice_allocation='shared256-central-parameters',
                    status='source_candidate_requires_build_timing_and_board_acceptance')
    manifest['sources'] = {p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(target.rglob('*')) if p.is_file() and p != manifest_path}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
