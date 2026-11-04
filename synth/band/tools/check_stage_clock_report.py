"""Verify actual PnR clocks independently of synthesis's default clock report."""
from pathlib import Path
import re,json,hashlib,datetime,html,sys

def clock_periods(text):
    section=re.search(r'name="Clock_Report".*?(<table.*?</table>)',text,re.S)
    if not section:raise ValueError('Missing final clock summary')
    clocks={}
    for row in re.findall(r'<tr>(.*?)</tr>',section[1],re.S):
        # Gowin omits some closing td tags; split at opening tags instead.
        cells=[html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.split(r'<td[^>]*>',row)[1:]]
        if len(cells)>=4:
            if cells[1] in clocks:raise ValueError('Duplicate clock '+cells[1])
            clocks[cells[1]]=float(cells[3])
    return clocks

def check(text,expected):
    clocks=clock_periods(text)
    if set(clocks)!=set(expected):raise ValueError('Clock set mismatch: '+repr(clocks))
    for name,period in expected.items():
        if abs(clocks[name]-period)>0.001:raise ValueError('Clock period mismatch: '+repr(clocks))
    return clocks

if __name__=='__main__':
    b=Path(__file__).resolve().parents[1]
    result=json.loads((b/'evidence/stage_timing/result.json').read_text())
    if result['status']=='running':raise SystemExit('PnR still running; no acceptance')
    report=Path(result['build'])/'impl/pnr/band_stage_tr_content.html'
    expected={'core_clk':20.0,'mic_clk':325.520833}
    record=dict(status='failed',updated=datetime.datetime.now().isoformat(),expected_clock_period_ns=expected,
        scope='Final internal PnR clock-table validation only; no external timing/physical acceptance',report=str(report))
    try:
        raw=report.read_bytes();record['report_sha256']=hashlib.sha256(raw).hexdigest()
        record['actual_clock_period_ns']=check(raw.decode('utf-8',errors='replace'),expected)
        record['status']='passed_clock_table_only'
    except Exception as exc:record['error']=str(exc)
    (b/'evidence/stage_timing/constraint_scope_check.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2));sys.exit(0 if record['status']=='passed_clock_table_only' else 1)
