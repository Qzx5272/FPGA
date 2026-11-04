"""Negative pin-audit fixtures; never a board acceptance report."""
from pathlib import Path
import copy,html,json,hashlib,datetime
from audit_pt8211_onboard import rows,check_pins

band=Path(__file__).resolve().parents[1]
baseline=Path('D:/StarclusterBuilds/pt8211_onboard_pnr_986a1e6784b5/impl/pnr/pt8211_onboard.pin.html')
text=baseline.read_text(encoding='utf-8')
assert len(check_pins(text))==15
section=text.split('name="Pinout_by_Port_Name"',1)[1].split('</table>',1)[0]
data=[r for r in rows(section) if len(r)>=17 and r[0]!='Port Name']
template=next(r for r in data if r[0]=='uart_rx_pin')
for name,pin in [('key_play_n','K16'),('key_stop_n','F15'),('key_panic_n','G15')]:
    row=list(template);row[0]=name;row[1]='';row[2]=pin;data.append(row)
def render(records):
    return 'GW5AST-LV138FPG676AC1/I0<a name="Pinout_by_Port_Name"></a><table>'+''.join('<tr>'+''.join('<td>'+html.escape(x)+'</td>' for x in r)+'</tr>' for r in records)+'</table>'
assert len(check_pins(render(data),True))==18
rejected=[]
def reject(name,records,controls=True):
    try:check_pins(render(records),controls)
    except AssertionError:rejected.append(name)
    else:raise AssertionError('Unsafe fixture accepted: '+name)
reject('18pins_cannot_use_15pin_profile',data,False)
reject('15pins_cannot_use_18pin_profile',data[:-3])
for offset in (1,2,3):
    for label,column,value in [('wrong_pin',2,'P16'),('automatic_pin',3,'N'),('output_direction',4,'out'),('wrong_voltage',16,'1.8'),('missing_pullup',9,'NONE'),('wrong_standard',7,'LVCMOS18')]:
        bad=copy.deepcopy(data);bad[-offset][column]=value
        reject(data[-offset][0]+':'+label,bad)
reject('duplicate_port',data+[data[-1]])
reject('missing_panic',data[:-1])
bad=copy.deepcopy(data);bad[-1][0]='unreviewed_input';reject('unknown_port',bad)
record=dict(status='passed',created=datetime.datetime.now().isoformat(),
 scope='Synthetic18-pin profiles and negative mutations, plus existing15-pin report parser regression; not new board pins/timing acceptance',
 rejected_cases=rejected,baseline_report_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
 sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),band/'tools/audit_pt8211_onboard.py']})
out=band/'evidence/onboard_pin_profiles';out.mkdir(exist_ok=True)
(out/'result.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
