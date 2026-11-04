"""Recompute archived diagnostic spectra; do not infer board or ensemble capacity."""
from pathlib import Path
import hashlib
import json
import numpy as np

band = Path(__file__).resolve().parents[1]
root = band.parents[1]
rows = []
for path in sorted((band / 'evidence').glob('pool*verilated.json')):
    record = json.loads(path.read_text())
    n = record['partials']
    current = {}
    for name, digest in record['sources'].items():
        choices = [band / 'rtl' / name, root / 'synth/rtl' / name, band / 'tests' / name]
        source = next((p for p in choices if p.is_file()), None)
        current[name] = bool(source and hashlib.sha256(source.read_bytes()).hexdigest() == digest)
    samples = path.with_name(path.stem + '_samples.txt')
    row = dict(report=str(path), report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
               partials=n, current_recorded_sources=current,
               source_coverage_complete='partial_ram16.v' in record['sources'])
    if not samples.exists() or hashlib.sha256(samples.read_bytes()).hexdigest() != record.get('sample_sha256'):
        row['status'] = 'missing_or_changed_raw_samples'
    else:
        x = np.loadtxt(samples)[-131072:]
        if len(x) != 131072 or not np.isfinite(x).all():
            raise ValueError('Invalid raw samples: ' + str(samples))
        spectrum = abs(np.fft.rfft(x)) * 2 / len(x)
        spacing = record.get('fft_bin_spacing', 1 if n > 16384 else 3 if n > 8192 else 5)
        bins = 50 + spacing * np.arange(n)
        targets = 45000 + (np.arange(n) * 37) % 15000 if record.get('diverse_envelopes') else 60000
        divisor = record.get('normalization_divisor', n)
        expected = 131071 * (targets / 65536) * 64 / divisor
        relative = abs(spectrum[bins] - expected) / expected
        row.update(status='passed_raw_spectrum' if np.all(relative < .03) else 'failed_raw_spectrum',
                   verified_peaks=int(np.count_nonzero(relative < .03)),
                   maximum_relative_error=float(relative.max()),
                   maximum_frequency_hz=float(bins[-1] * 48000 / len(x)),
                   sample_sha256=record['sample_sha256'])
    rows.append(row)
output = band / 'evidence/pool_spectrum_reaudit_20261026.json'
if output.exists():
    raise ValueError('Preserve existing evidence')
output.write_text(json.dumps(dict(rows=rows, scope='Recomputed diagnostic raw spectra. Source mismatches or incomplete source coverage prevent current-RTL acceptance. No physical, full-band, fixed sample cadence or interactive-control proof.'), indent=2))
print(json.dumps(rows, indent=2))
