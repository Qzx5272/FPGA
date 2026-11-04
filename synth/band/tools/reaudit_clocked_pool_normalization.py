"""Recheck preserved full-clock samples with the documented power-of-two gain."""
from pathlib import Path
import argparse,hashlib,json
import numpy as np
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('report',type=Path);a=ap.parse_args()
r=json.loads(a.report.read_text());assert r['returncode']==0 and 'PASS capacity=' in r['log']
root=Path(__file__).resolve().parents[3]
for name,h in r['source_sha256'].items():
 if name.endswith(('.v','.vh')):assert hashlib.sha256((root/name).read_bytes()).hexdigest()==h,name
rtl=(root/'synth/band/rtl/partial_pool.v').read_text()
assert 'sample_out<=combined>>>(LANE_BITS+ADDRESS_BITS-6);' in rtl
samples=a.report.with_suffix('.samples.txt');assert hashlib.sha256(samples.read_bytes()).hexdigest()==r['sample_sha256']
x=np.loadtxt(samples);assert len(x)==135168
n=r['partials'];bins=50+r['frequency_step_bins']*np.arange(n);assert bins[-1]<65536
amplitude=abs(np.fft.rfft(x[-131072:]))[bins]*2/131072
divisor=1<<(r['lane_bits']+r['address_bits'])
expected=131071*((45000+(np.arange(n)*37)%15000)/65536)*64/divisor
error=abs(amplitude-expected)/expected
out=a.report.with_name(a.report.stem+'_normalization_review.json');assert not out.exists()
record={'status':'passed_corrected_reference' if np.all(error<.03) else 'failed',
 'original_report_sha256':hashlib.sha256(a.report.read_bytes()).hexdigest(),'original_status':r['status'],
 'sample_sha256':r['sample_sha256'],'partials':n,'normalization_divisor':divisor,
 'rtl_gain_expression':'combined >>> (LANE_BITS+ADDRESS_BITS-6)',
 'old_reference_relative_bias':1-n/divisor,'maximum_relative_error':float(error.max()),
 'verified_peaks':int(np.count_nonzero(error<.03)),'threshold_unchanged':.03,
 'simulation_rerun':False,'rtl_changed':False,'original_failure_preserved':True,
 'scope':'Corrected mathematical normalization of existing completed fixed-cadence RTL samples, not board timing or whole-band acceptance'}
out.write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2));raise SystemExit(record['status']=='failed')
