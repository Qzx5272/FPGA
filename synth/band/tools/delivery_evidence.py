"""Select completed, matching evidence without promoting running tests."""
import json,re
def read(path):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
def best_band_record(band,digest):
    records=[]
    for path in (band/'evidence').glob('hardware_band*.json'):
        record=read(path)
        if record.get('status')=='passed' and record.get('bitstream_sha256')==digest:
            records.append((record.get('stress_seconds',0),record))
    if records:return max(records,key=lambda item:item[0])[1]
    return dict(status='not_verified',error='No completed passing board record for the selected bitstream')
def host_test_count(band):
    record=read(band/'evidence/host_tests.json')
    match=re.search(r'Ran (\d+) tests?',record.get('output',''))
    return int(match[1]) if record.get('status')=='passed' and match else 0
