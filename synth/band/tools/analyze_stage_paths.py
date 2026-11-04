"""Summarize reported critical paths; never confuse top-N paths with all endpoints."""
from pathlib import Path
from collections import Counter
import argparse,json,re,hashlib
ap=argparse.ArgumentParser();ap.add_argument('build');ap.add_argument('--base',choices=('band_stage','combined_workstation'),default='band_stage');a=ap.parse_args()
build=Path(a.build).resolve();p=build/'impl/pnr'/(a.base+'.timing_paths');html=build/'impl/pnr'/(a.base+'_tr_content.html')
paths=[]
for block in p.read_text(errors='replace').split('====='):
 lines=block.strip().splitlines()
 if not lines or lines[0] not in ('SETUP','HOLD'):continue
 names=[line for line in lines if '/' in line]
 if len(names)<2:raise ValueError('Missing path endpoints')
 launch,capture=names[0],names[-1];kind='unclassified'
 if re.search(r'/fifo/wgray_\d',launch) and '/fifo/wgray_r1_' in capture:kind='async_write_gray_to_first_sync'
 elif re.search(r'/fifo/rgray_\d',launch) and '/fifo/rgray_w1_' in capture:kind='async_read_gray_to_first_sync'
 elif '/fifo/memory_' in launch and re.search(r'/input_audio/(latest|held)_',capture):kind='async_fifo_payload_to_reader'
 elif '/local_inputs.pads/' in launch and '/local_inputs.pads/' in capture:kind='pad_frontend_internal'
 paths.append(dict(check=lines[0],slack_ns=float(lines[1]),launch=launch,capture=capture,classification=kind))
text=html.read_text(encoding='utf-8',errors='replace');totals={}
for check in ('Setup','Hold'):
 m=re.search('Numbers of '+check+r' Violated Endpoints</td>\s*<td>(\d+)</td>',text)
 if not m:raise ValueError('Missing final timing summary')
 totals[check.lower()]=int(m[1])
negative=[x for x in paths if x['slack_ns']<0]
record=dict(status='analysis_only',build=str(build),scope='Vendor reported top-N path diagnosis; no timing exception applied, no CDC/physical acceptance',total_violated_endpoints=totals,
 reported_negative_paths=len(negative),reported_negative_classes=dict(Counter(x['classification'] for x in negative)),paths=paths,
 sources={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (p,html,Path(__file__))})
out=Path(__file__).resolve().parents[1]/'evidence/stage_path_analysis';out.mkdir(exist_ok=True)
(out/(build.name+'.json')).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ('paths','sources')},indent=2))
