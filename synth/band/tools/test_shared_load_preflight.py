"""Exercise the offline load guard against actual candidate source snapshots."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from shared_load_preflight import validate_shared_load

band = Path(__file__).resolve().parents[1]
root = band.parents[1]
exports = root / 'output/final_workstation_20261022'
checks = []
for suffix, layout in [('shared_c38c151eeea4', 'replicated_parameters'),
                      ('central_2c13b385c9c4', 'central_parameters')]:
    with tempfile.TemporaryDirectory(prefix='shared_load_guard_') as tmp:
        release = Path(tmp)
        shutil.copytree(exports / ('offline_workstation_pt8211_' + suffix) / 'rtl',
                        release / 'source_snapshot')
        manifest = {'snapshot_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (release / 'source_snapshot').iterdir() if p.is_file()}}
        assert validate_shared_load(release, manifest)['layout'] == layout
        checks.append(layout + ': accepts matching source fixture')
        path = release / 'source_snapshot/shared_note_allocator.v'
        path.write_bytes(path.read_bytes() + b'\n// changed\n')
        try:
            validate_shared_load(release, manifest)
        except RuntimeError as exc:
            assert 'hashed shared_note_allocator.v' in str(exc)
        else:
            raise AssertionError('Modified allocator accepted')
        checks.append(layout + ': rejects modified dependency')
selected = 'pt8211_dvi_59c963cc2112'  # Immutable quota-layout negative fixture.
release = band / 'release' / selected
manifest = json.loads((release / 'manifest.json').read_text(encoding='utf-8'))
try:
    validate_shared_load(release, manifest)
except RuntimeError as exc:
    assert 'shared router' in str(exc)
else:
    raise AssertionError('Old quota release accepted')
checks.append('historical quota release rejected')
selected = json.loads((band / 'CURRENT_RELEASE.json').read_text())['release']
release = band / 'release' / selected
manifest = json.loads((release / 'manifest.json').read_text(encoding='utf-8'))
assert validate_shared_load(release, manifest)['layout'] == 'central_parameters'
checks.append('selected central-parameter release accepted')
result = {'status': 'passed', 'created': datetime.datetime.now().isoformat(),
          'checks': checks, 'scope': 'Offline source guard only; no USB access or board acceptance',
          'sources': {name: hashlib.sha256((band / 'tools' / name).read_bytes()).hexdigest()
                      for name in ('shared_load_preflight.py', 'hardware_check.py', 'test_shared_load_preflight.py')}}
out = band / 'evidence/shared_load_guard' / ('selected_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
