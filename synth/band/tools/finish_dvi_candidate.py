"""Await existing DVI jobs, then run gated small and whole timing; never program."""
from pathlib import Path
import argparse,json,time,sys,subprocess,datetime,hashlib
ap=argparse.ArgumentParser()
ap.add_argument('simulation_report',type=Path)
ap.add_argument('combined_build',type=Path)
ap.add_argument('small_build',type=Path)
a=ap.parse_args();b=Path(__file__).resolve().parents[1]
syn=b/'evidence/combined_workstation_synthesis'/a.combined_build.name.removeprefix('combined_workstation_syn_')/'result.json'
key=a.combined_build.name.removeprefix('combined_workstation_syn_')
out=b/'evidence/dvi_pipeline'/key;out.mkdir(parents=True,exist_ok=False)
record=dict(status='waiting',simulation=str(a.simulation_report.resolve()),synthesis=str(syn),small_build=str(a.small_build),combined_build=str(a.combined_build),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Orchestration of source-gated existing jobs;not hardware acceptance')
def save(status):
 record.update(status=status,updated=datetime.datetime.now().isoformat())
 (out/'result.json').write_text(json.dumps(record,indent=2))
save('waiting_for_existing_jobs');limit=time.monotonic()+1800
try:
 while time.monotonic()<limit:
  records=[]
  for p in (a.simulation_report,syn):
   try:records.append(json.loads(p.read_text(encoding='utf-8')))
   except (FileNotFoundError,json.JSONDecodeError):records.append({})
  if any(x.get('status','').startswith('failed') for x in records):raise RuntimeError('Prerequisite failed')
  if records[0].get('status')=='passed' and records[1].get('status')=='passed_synthesis_only':break
  time.sleep(15)
 else:raise TimeoutError('Existing jobs did not finish in observation window;do not restart without inspecting handles')
 for status,tool,args in [('running_small_timing','build_dvi_output_timing.py',[str(a.small_build)]),('running_combined_timing','build_dvi_workstation_timing.py',[str(a.combined_build),'--cdc-hold'])]:
  save(status);print(status,flush=True)
  subprocess.run([sys.executable,str(b/'tools'/tool),*args],check=True)
 save('passed_internal_timing_commands_only')
except Exception as error:
 record['error']=str(error);save('failed_or_incomplete');raise
