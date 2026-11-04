from pathlib import Path
import os,sys,subprocess,json
band=Path(__file__).resolve().parents[1];root=band.parents[1];sys.path.insert(0,str(band/'host'))
from protocol import Event
out=Path('D:/StarclusterBuilds/v6_panel_tests');out.mkdir(exist_ok=True)
(out/'ingress_frames.mem').write_text('\n'.join(f'{v:02x}' for e in [Event(11,source=1),Event(11,source=3),Event(127)] for v in e.encode()),encoding='utf-8')
cad=root/'tmp/oss-cad-suite';env=dict(os.environ);env['PATH']=str(cad/'bin')+os.pathsep+str(cad/'lib')+os.pathsep+env['PATH'];results=[]
for name,files in [
 ('tb_panel_v6',[band/'experimental/panel_v6/quadrature_encoder.v',band/'experimental/panel_v6/panel_controls.v']),
 ('tb_dual_uart_v6',[band/'rtl/event_receiver.v',band/'experimental/panel_v6/dual_uart_events.v']),
 ('tb_space_v6',[band/'experimental/panel_v6/stereo_space.v']),
 ('tb_capture_v6',[band/'experimental/panel_v6/event_capture_fifo.v'])]:
 files=files+[band/'tests'/(name+'.sv')];exe=out/(name+'.vvp')
 commands=[[str(cad/'bin/iverilog.exe'),'-g2012','-s',name,'-o',str(exe),*map(str,files)],[str(cad/'bin/vvp.exe'),str(exe)]]
 logs=[]
 for cmd in commands:
  p=subprocess.run(cmd,cwd=out,env=env,capture_output=True,text=True,timeout=30);logs.append(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(''.join(logs))
 print(''.join(logs));results.append(dict(test=name,status='passed',log=''.join(logs)))
(out/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
