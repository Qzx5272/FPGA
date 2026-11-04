"""Offline source-integrity gate for the single-role hardware load test.

This recognizes reviewed source layouts; it does not prove synthesized reachability
or timing, which remain separate release gates.
"""
import hashlib


def validate_shared_load(release, manifest):
    checked = {}

    def source(name):
        path = release / 'source_snapshot' / name
        expected = manifest.get('snapshot_sha256', {}).get(name)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f'Single-part load requires hashed {name}; no USB access')
        checked[name] = expected
        return path.read_text(encoding='utf-8')

    core = source('band_singer_core.sv')
    if 'voice_bank #(' in core or 'shared_bank_dispatch #(' not in core:
        raise RuntimeError('Selected release lacks the shared router; no USB access')
    if 'central_voice_bank unit' in core and 'shared_role_controls role_controls' in core:
        layout = 'central_parameters'
        bank = source('central_voice_bank.v')
        source('shared_role_controls.v')
    elif 'shared_voice_bank unit' in core:
        layout = 'replicated_parameters'
        bank = source('shared_voice_bank.v')
    else:
        raise RuntimeError('Selected release has no reviewed shared bank layout; no USB access')
    if 'shared_note_allocator allocator' not in bank or 'shared_band_renderer #(' not in bank:
        raise RuntimeError('Shared bank dependencies do not match reviewed layout; no USB access')
    for name in ('shared_bank_dispatch.v', 'shared_note_allocator.v', 'shared_band_renderer.v'):
        source(name)
    return {'layout': layout, 'source_sha256': checked,
            'scope': 'Source integrity/layout only; not netlist, timing or hardware acceptance'}
