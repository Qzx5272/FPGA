"""Inspect native OSER recovery/removal paths; never promote a board release."""
from pathlib import Path
import argparse,hashlib,html,json,math,re

def plain(s):return html.unescape(re.sub('<[^>]+>','',s)).strip()

def review(raw):
    paths=[]
    for command,section in re.findall(r'<h4>Report Command:(.*?)</h4>(.*?)(?=<h4>|\Z)',raw,re.S):
        command=plain(command)
        if not command.startswith('report_timing '):continue
        kind=next((x for x in ('recovery','removal') if '-'+x in command),None)
        if not kind:continue
        for part in section.split('<p><b>Path Summary:</b></p>')[1:]:
            table=re.search(r'<table[^>]*>(.*?)</table>',part,re.S)
            if not table:continue
            rows=[list(map(plain,re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',row,re.S))) for row in re.findall(r'<tr[^>]*>(.*?)</tr>',table[1],re.S)]
            values={row[0]:row[1] for row in rows if len(row)==2}
            endpoint=values.get('To','')
            lane=re.fullmatch(r'workstation/video_output/transmitter/channels\[(\d)\]\.serializer',endpoint)
            if not lane:continue
            slack,arrival,required=[float(values[k]) for k in ('Slack','Data Arrival Time','Data Required Time')]
            assert all(math.isfinite(x) for x in (slack,arrival,required)), 'Nonfinite timing'
            computed=required-arrival if kind=='recovery' else arrival-required
            assert abs(slack-computed)<=.003, 'Inconsistent native timing arithmetic'
            arrival_path=part.split('<p><b>Data Arrival Path:</b></p>',1)[1].split('<p><b>Data Required Path:</b></p>',1)[0]
            stages=sorted(set(int(n) for n in re.findall(r'reset_buffer_(\d+)',plain(arrival_path))))
            paths.append(dict(kind=kind,lane=int(lane[1]),source=values['From'],endpoint=endpoint,
                launch=values['Launch Clk'],latch=values['Latch Clk'],slack_ns=slack,
                arrival_ns=arrival,required_ns=required,buffer_stages=stages,command=command))
    coverage={(p['kind'],p['lane'],p['latch']) for p in paths}
    missing=[dict(kind=k,lane=n,edge=edge) for k in ('recovery','removal') for n in range(3)
             for edge in ('serial_clk:[R]','serial_clk:[F]') if (k,n,edge) not in coverage]
    missing_pixel=[dict(kind=k,lane=n,edge='display_clk:[R]') for k in ('recovery','removal')
                   for n in range(3) if (k,n,'display_clk:[R]') not in coverage]
    negative=[p for p in paths if p['slack_ns']<0]
    return dict(status='native_paths_nonnegative_pending_review' if paths and not missing and not missing_pixel and not negative else 'not_accepted',
        paths=paths,missing_serial_checks=missing,missing_pixel_checks=missing_pixel,negative_paths=len(negative),
        scope='Native reported OSER reset paths only. Requires full setup/hold/pulse, clock/pin and physical-cell review; not a board release gate.')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('build',type=Path);a=ap.parse_args()
    source=a.build/'impl/pnr/pt8211_onboard_tr_content.html'
    record=review(source.read_text(encoding='utf-8'));record['report_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    out=Path(__file__).resolve().parents[1]/'evidence/pt8211_onboard_timing'/a.build.name.removeprefix('pt8211_onboard_pnr_')/'native_reset_paths.json'
    out.write_text(json.dumps(record,indent=2))
    print(json.dumps({k:v for k,v in record.items() if k!='paths'},indent=2));print(out)
    raise SystemExit(record['status']=='not_accepted')
