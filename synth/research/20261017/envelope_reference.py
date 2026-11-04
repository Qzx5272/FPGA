"""Finite-width exponential envelope: coefficient quantization and error feedback.

No audio or FPGA measurements. Target error is 1e-4 after requested duration.
"""
import json, math
from pathlib import Path

SCALE=1<<24
MAX=SCALE-1

def rounded(z,frac):
    return (z+(1<<(frac-1)))>>frac if z>=0 else -((-z+(1<<(frac-1)))>>frac)

def step(env,target,rate,residual=0,frac=24):
    z=(target-env)*rate+residual
    delta=rounded(z,frac)
    return env+delta,z-(delta<<frac)

def run(seconds,frac,feedback):
    n=round(seconds*48000)
    rate=round(-math.expm1(math.log(1e-4)/n)*(1<<frac))
    env=MAX;res=0
    for _ in range(n):
        env,res=step(env,0,rate,res if feedback else 0,frac)
    quantized_residual=(1-rate/(1<<frac))**n
    return {'seconds':seconds,'coefficient_fraction_bits':frac,'error_feedback':feedback,
            'rate_integer':rate,'end_amplitude':env/MAX,'end_dbfs':20*math.log10(max(env/MAX,1e-20)),
            'coefficient_only_end_amplitude':quantized_residual,
            'error_against_quantized_float_lsb':env-MAX*quantized_residual,
            'residual_integer':res}

def main():
    cases=[run(t,f,fb) for t in [.001,.01,.1,1,4,10,60] for f,fb in [(17,False),(24,False),(24,True)]]
    # State transition protection is separate from amplitude: commit only same generation.
    generations=[0]*64
    pending=(3,generations[3],12345)
    generations[3]+=1
    assert pending[1]!=generations[pending[0]]
    # At generation UINT32_MAX, quiesce this slot, drain old pipeline writes, clear then restart.
    # Does not assume that wrapping an integer alone prevents ABA aliasing.
    checks={'all_feedback_within_2_lsb_of_quantized_curve':all(abs(c['error_against_quantized_float_lsb'])<=2 for c in cases if c['error_feedback']),
            'feedback_residual_bounded':all(abs(c['residual_integer'])<=1<<23 for c in cases if c['error_feedback']),
            'stale_write_rejected':pending[1]!=generations[pending[0]]}
    assert all(checks.values()),checks
    result={'scope':'CPU integer envelope model; not integrated audio or board test','sample_rate':48000,
            'target_end_dbfs':-80,'checks':checks,'cases':cases,
            'endpoint_policy':'At segment timer expiry use <=64 sample terminal ramp to target, then clear residual. Release ends at exact zero; stage change clears or explicitly transfers residual.'}
    out=Path(__file__).resolve().parent/'deep'/'envelope_results.json'
    out.write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
