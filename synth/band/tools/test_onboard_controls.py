"""Exercise actual board-key wrapper and exported engine; not a pin/timing test."""
from pathlib import Path
import json,hashlib,datetime,subprocess,os,shutil,time,sys
band=Path(__file__).resolve().parents[1];root=band.parents[1]
export=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'output/final_workstation_20261022/offline_workstation_pt8211_dvi_confluence'
manifest=json.loads((export/'export_manifest.json').read_text(encoding='utf-8'))
for name,h in manifest['sources'].items():
    assert hashlib.sha256((export/name).read_bytes()).hexdigest()==h,name
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
out=band/'evidence/onboard_controls'/stamp;out.mkdir(parents=True)
build=Path('D:/StarclusterBuilds')/('onboard_controls_'+stamp)
shutil.copytree(export/'rtl',build)
for p in export.glob('*.mem'):shutil.copy2(p,build/p.name)
shell=band/'experimental/audio_visual/onboard_controls/board_pt8211_controls_top.sv'
shutil.copy2(shell,build/shell.name)
tb='''`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg kp=1,ks=1,ke=1;
wire bck,ws,din;
GSR GSR(.GSRI(1'b1));
board_pt8211_controls_top dut(.clk(clk),.uart_rx_pin(1'b1),
 .key_play_n(kp),.key_stop_n(ks),.key_panic_n(ke),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din));
// Accelerated debounce only. The production default remains250000cycles.
defparam dut.workstation.band.engine.local_inputs.play_button.STABLE_CYCLES=4;
defparam dut.workstation.band.engine.local_inputs.stop_button.STABLE_CYCLES=4;
integer np=0,ns=0;
always @(negedge clk)begin
 if(dut.workstation.band.engine.local_play_pulse)np=np+1;
 if(dut.workstation.band.engine.local_stop_pulse)ns=ns+1;
end
task settle;begin repeat(100)@(negedge clk);end endtask
initial begin
 wait(!dut.workstation.band.engine.rst);
 wait(dut.workstation.band.engine.playing);settle;
 if(np||ns||dut.workstation.band.engine.panic)$fatal(1,"idle keys asserted");
 // One-clock bounce must not stop transport.
 ks=0;@(negedge clk);ks=1;settle;
 if(ns||!dut.workstation.band.engine.playing)$fatal(1,"bounce accepted");
 ks=0;settle;
 if(ns!=1||dut.workstation.band.engine.playing)$fatal(1,"stop press/hold");
 settle;if(ns!=1)$fatal(1,"held stop repeated");
 ks=1;settle;kp=0;settle;
 if(np!=1||!dut.workstation.band.engine.playing)$fatal(1,"play press");
 settle;if(np!=1)$fatal(1,"held play repeated");
 kp=1;settle;ke=0;repeat(4)@(negedge clk);
 if(!dut.workstation.band.engine.panic)$fatal(1,"panic synchronizer");
 settle;
 if(dut.workstation.band.engine.playing||dut.workstation.band.engine.active_voices!=0)$fatal(1,"panic failed to clear");
 kp=0;settle;
 if(dut.workstation.band.engine.playing)$fatal(1,"play escaped held panic");
 kp=1;ke=1;settle;
 if(dut.workstation.band.engine.playing)$fatal(1,"panic release restarted");
 kp=0;settle;
 if(!dut.workstation.band.engine.playing||np!=3)$fatal(1,"fresh play failed");
 ks=0;settle;
 if(dut.workstation.band.engine.playing||ns!=2)$fatal(1,"final stop failed");
 $display("PASS actual board shell: idle,bounce,hold,stop,play,panic priority,no auto resume,fresh restart");$finish;
end
initial begin #4000000;$fatal(1,"timeout");end
endmodule
'''
(build/'tb.v').write_text(tb);(out/'tb.v').write_text(tb)
binary=root/'tmp/oss-cad-suite/bin'
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
record=dict(status='running',build=str(build),scope='Actual exported fulltop and proposed active-low button shell; debounce accelerated to4cycles. No physical pin,5ms bounce duration,metastability or timing acceptance.',
 sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [*build.glob('*.v'),*build.glob('*.sv'),*build.glob('*.vh'),*build.glob('*.mem'),vendor,Path(__file__)]})
report=out/'result.json';report.write_text(json.dumps(record,indent=2));print(build,flush=True)
try:
    run=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-I',str(build),'-s','tb','-o','test.vvp',*map(str,build.glob('*.v')),*map(str,build.glob('*.sv')),str(vendor)],cwd=build,env=env,capture_output=True,text=True,timeout=120)
    (out/'compile.log').write_text(run.stdout+run.stderr);assert run.returncode==0,'compile failed'
    start=time.monotonic()
    with (out/'run.log').open('w') as log:
        run=subprocess.run([str(binary/'vvp.exe'),'test.vvp'],cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    record['elapsed_seconds']=time.monotonic()-start;record['log']=(out/'run.log').read_text()
    assert run.returncode==0 and 'PASS actual board shell:' in record['log'],record['log']
    record['status']='passed'
except Exception as e:
    record.update(status='failed',error=str(e));raise
finally:
    record['finished']=datetime.datetime.now().isoformat();report.write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='sources'},indent=2))
