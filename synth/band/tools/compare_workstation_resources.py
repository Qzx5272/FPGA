"""Compare frozen routed reports, retaining timing and configuration limits."""
from pathlib import Path
import argparse,hashlib,json,re
from timing_pulse import pulse_rows


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read_release(path):
    manifest_path=path/'manifest.json';manifest=json.loads(manifest_path.read_text())
    report=path/'pt8211_onboard.rpt.txt';timing=path/'pt8211_onboard_tr_content.html'
    for p in (report,timing):
        assert sha(p)==manifest['evidence_sha256'][p.name], ('Frozen report changed',p)
    text=report.read_text();resources={}
    for key,label in [('logic','Logic'),('ff','Register'),('cls','CLS'),('ram','BSRAM'),('dsp','DSP')]:
        match=re.search(r'^\s*'+re.escape(label)+r'\s*\|\s*(\d+)/',text,re.M)
        assert match,('Missing resource',label)
        resources[key]=int(match[1]);assert resources[key]==manifest['physical_resources'][key]
    rows=pulse_rows(timing.read_text(encoding='utf-8'))
    return dict(release=path.name,build_id=manifest['build_id'],hardware_profile=manifest['hardware_profile'],
        top_module=manifest['top_module'],resources=resources,
        reported_negative_pulse_paths=sum(r['slack_ns']<0 or r['actual_ns']<r['required_ns'] for r in rows),
        bitstream_sha256=manifest['bitstream_sha256'],manifest_sha256=sha(manifest_path),
        resource_report_sha256=sha(report),timing_report_sha256=sha(timing))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('before',type=Path);ap.add_argument('after',type=Path);a=ap.parse_args()
    before=read_release(a.before);after=read_release(a.after)
    assert before['hardware_profile']==after['hardware_profile'] and before['top_module']==after['top_module']
    deltas={k:dict(before=v,after=after['resources'][k],reduction=v-after['resources'][k],
                   reduction_percent=100*(v-after['resources'][k])/v) for k,v in before['resources'].items()}
    record=dict(status='analysis_only_not_board_acceptance',before=before,after=after,deltas=deltas,
        scope='Frozen routed resource comparison of same board shell/profile. Firmware, score and mapping differ; do not attribute every delta to one optimization or claim physical audio/stability equivalence. Independent exact96s PCM proof covers the four-engine core render only.')
    digest=hashlib.sha256((before['manifest_sha256']+after['manifest_sha256']+sha(Path(__file__))).encode()).hexdigest()[:12]
    out=Path(__file__).resolve().parents[1]/'evidence/resource_comparison'/digest;out.mkdir(parents=True,exist_ok=False)
    (out/'result.json').write_text(json.dumps(record,indent=2));(out/'compare_snapshot.py').write_bytes(Path(__file__).read_bytes())
    print(out)
    for key,value in deltas.items():print(key,value)
