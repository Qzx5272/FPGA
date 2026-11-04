"""Bind software acceptance to current source; never upgrade an older result implicitly."""
from pathlib import Path
import json,hashlib,re,datetime,sys
root=Path(__file__).resolve().parents[3];band=root/'synth/band';ev=band/'evidence'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={};details={}
def current_render(record):
    for name,digest in record.get('source_hashes',{}).items():
        candidates=[band/'rtl'/name,band/'tests'/name,root/'synth/rtl'/name]
        p=next((p for p in candidates if p.exists()),None)
        if p is None or sha(p)!=digest:return False
    return bool(record.get('source_hashes'))
releases=[]
for p in (band/'release').glob('band_*/manifest.json'):
    m=json.loads(p.read_text());match=bool(m.get('snapshot_sha256'))
    for relative,digest in m.get('source_sha256',{}).items():
        source=band.parent/Path(relative.replace('\\','/'))
        if not source.exists() or sha(source)!=digest:match=False
    for name,digest in m.get('snapshot_sha256',{}).items():
        source=p.parent/'source_snapshot'/name
        if not source.exists() or sha(source)!=digest:match=False
    if match and m.get('setup_violations')==0 and m.get('hold_violations')==0 and sha(p.parent/'starcluster_band.fs')==m['bitstream_sha256']:
        releases.append(p.parent.name)
checks['baseline_source_setup_hold_bound_release']=bool(releases);details['matching_releases']=releases
tests=json.loads((ev/'rtl_tests.json').read_text())
expected=set('delay allocator ownership partial pool renderer protocol board scanner pads store upload i2s24 cdc local workstation controls dispatch telemetry board_burst'.split())
good=[]
for t in tests:
    match=all((root/Path(n.replace('\\','/'))).exists() and sha(root/Path(n.replace('\\','/')))==h for n,h in t['sources'].items())
    if match and t['returncode']==0 and 'PASS' in t['output'] and 'FAIL' not in t['output']:good.append(t['test'])
checks['all_20_module_tests_current_source']=expected<=set(good);details['current_module_tests']=good
renders=[]
for p in ev.glob('band_*.json'):
    try:m=json.loads(p.read_text())
    except (ValueError,UnicodeError):continue
    if m.get('status')=='passed' and current_render(m):renders.append((p,m))
details['current_passed_renders']=[p.name for p,m in renders]
for mode in ('fast','full'):
    matches=[(p,m) for p,m in renders if m.get('mode')==mode and m.get('duration_seconds',0)>=97]
    checks['whole_song_'+mode]=bool(matches)
    if matches:details['whole_song_'+mode]=matches[-1][0].name
full=[m for p,m in renders if m.get('mode')=='full' and m.get('duration_seconds')==97]
fast=[m for p,m in renders if m.get('mode')=='fast' and m.get('duration_seconds')==97]
checks['whole_song_full_fast_pcm_identity']=bool(full and fast and full[-1]['pcm_sha256']==fast[-1]['pcm_sha256'])
stress=[(p,m) for p,m in renders if m.get('mode')=='stress' and m.get('duration_seconds',0)>=60 and 'min_sustained_voices=256' in m.get('log','')]
checks['sustained_256_slots_59_seconds_plus_release']=bool(stress)
for mode in ('matrix','audition_fast'):
    passed=[]
    for p,m in renders:
        analysis=p.with_suffix('.analysis.json')
        if m.get('mode')==mode and analysis.exists():
            a=json.loads(analysis.read_text())
            if a.get('status')=='passed' and a.get('wav_sha256')==sha(p.with_suffix('.wav')):passed.append(p.name)
    checks['sound_analysis_'+mode]=bool(passed)
    details['sound_analysis_'+mode]=passed
host=ev/'host_tests.json'
if host.exists():
    h=json.loads(host.read_text());checks['host_interaction_tests']=h.get('status')=='passed' and all(sha(root/Path(n))==digest for n,digest in h['sources'].items())
else:checks['host_interaction_tests']=False
report=dict(updated=datetime.datetime.now().isoformat(),status='passed' if all(checks.values()) else 'incomplete',
            evidence_level='Baseline synth/band/rtl regression and recorded baseline setup/hold only; not selected shared PT8211/DVI workstation acceptance',checks=checks,details=details,
            final_workstation_accepted=False,
            final_workstation_authority='FINAL_READINESS.json',
            not_claimed=['selected workstation timing','minimum pulse width acceptance','physical download','analog quality','actual external peripherals','long-duration thermal stability','arbitrary lyric singing','runtime nonvolatile song writes'])
(ev/'software_acceptance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if '--require-pass' in sys.argv and report['status']!='passed':raise SystemExit(1)
