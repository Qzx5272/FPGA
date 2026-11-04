"""Reproducible finite-word-length design experiments; no audio claims."""
from pathlib import Path
import json, math, re
import numpy as np

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'deep';OUT.mkdir(exist_ok=True)
FS=48000
def db(x):return float(20*np.log10(max(float(x),1e-20)))
def spectrum_metrics(x,k):
    mag=np.abs(np.fft.rfft(x));fund=mag[k];others=mag.copy();others[k]=0;others[0]=0
    return {'sfdr_dbc':-db(others.max()/fund),'sinad_db':-db(np.linalg.norm(others)/fund)}
def dds_tests():
    source=(ROOT.parents[1]/'rtl'/'sine_function.vh').read_text()
    lut=np.array([int(h,16) for h in re.findall(r"sine=16'h([0-9a-f]+)",source)])
    lut=np.where(lut>=32768,lut-65536,lut)
    assert len(lut)==256
    hq=np.rint(np.sin(2*np.pi*np.arange(4097)/4096)*131071).astype(np.int64)
    n=65536;results=[]
    for k in [73,601,1361,5461,20001,29001]:
        phase=(np.arange(n,dtype=np.uint64)*np.uint64(k<<16))&np.uint64(0xffffffff)
        old=lut[(phase>>24).astype(np.int64)]
        index=(phase>>20).astype(np.int64);fraction=(phase&((1<<20)-1)).astype(np.int64)
        delta=hq[index+1]-hq[index]
        interp=hq[index]+((delta*fraction+(1<<19))>>20)
        results.append({'frequency_hz':k*FS/n,'legacy':spectrum_metrics(old,k),'hq4096_linear':spectrum_metrics(interp,k)})
    return results
def pole_tests():
    results=[]
    for q in (15,21,27):
        worst_cent=0;worst_bw=0;bad=0;worst=None
        for f in np.geomspace(50,18000,300):
            for bw in [5,10,30,50,100,250,500,1000,3000]:
                r=math.exp(-math.pi*bw/FS);b=round(2*r*math.cos(2*math.pi*f/FS)*(1<<q))/(1<<q)
                c=round(-r*r*(1<<q))/(1<<q)
                poles=np.roots([1,-b,-c]);rad=max(abs(poles))
                if rad>=1:bad+=1;continue
                theta=abs(np.angle(poles[0]));fq=theta*FS/(2*math.pi)
                if fq==0:bad+=1;continue
                cents=abs(1200*math.log2(fq/f));bq=-FS*math.log(rad)/math.pi
                if cents>worst_cent:worst_cent=cents;worst={'f_hz':float(f),'bw_hz':bw,'reconstructed_f_hz':float(fq)}
                worst_bw=max(worst_bw,abs(bq-bw))
        results.append({'coefficient_fraction_bits':q,'cases':2700,'invalid_or_real_pole_cases':bad,
                        'worst_frequency_error_cents':worst_cent,'worst_bandwidth_error_hz':worst_bw,'worst_frequency_case':worst})
    return results

def coupled_pole_tests():
    results=[]
    for q in (15,21,27):
        worst_cent=0;worst_bw=0;bad=0
        for f in np.geomspace(50,18000,300):
            for bw in [5,10,30,50,100,250,500,1000,3000]:
                r=math.exp(-math.pi*bw/FS);th=2*math.pi*f/FS
                a=round(r*math.cos(th)*(1<<q))/(1<<q)
                b=round(r*math.sin(th)*(1<<q))/(1<<q)
                rad=math.hypot(a,b)
                if rad>=1:bad+=1;continue
                fq=math.atan2(b,a)*FS/(2*math.pi)
                worst_cent=max(worst_cent,abs(1200*math.log2(fq/f)))
                worst_bw=max(worst_bw,abs(-FS*math.log(rad)/math.pi-bw))
        results.append({'coefficient_fraction_bits':q,'cases':2700,'unstable_cases':bad,
                        'worst_pole_angle_error_cents':worst_cent,'worst_bandwidth_error_hz':worst_bw})
    return results
def memory_budget(partials):
    # SDP 512x36: one read + one write per cycle, not two writes.
    lanes=8;depth=math.ceil(partials/lanes)
    state=lanes*math.ceil(depth/512)*math.ceil(256/36)
    # 8 pairs of 4096x18 sine endpoints can instead use 8 dual-port copies.
    sine=lanes*4
    rows={'partial_state':state,'dds_lut_copies':sine,'8_string_delays_2048x27':32,
          '8_fdn_delays_2048x27':32,'stereo_echo_4096x27':16,
          'event_and_track_state':12,'voice_and_patch_parameters':16,
          'vocal_glottal_parameter_tables':8,'control_tables_and_scratch':12}
    total=sum(rows.values())
    return {'partials':partials,'assumptions':'SDP depth/width allocation; no external DDR; LUT dual ports shared for adjacent samples',
            'blocks_by_use':rows,'bsram18k_blocks':total,'budget_blocks':340,'free_blocks':340-total,
            'passes_raw_block_budget':total<=340}
def main():
    result={'scope':'numerical/arithmetic design estimates only','dds_coherent_fft_N':65536,
            'dds':dds_tests(),'resonator_poles':pole_tests(),'coupled_resonator_poles':coupled_pole_tests(),
            'memory':[memory_budget(n) for n in (1024,4096,8192)]}
    (OUT/'numeric_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
