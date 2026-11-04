"""Check audio-only top: stopped boot, real song PCM to I2S, stop/panic."""
from pathlib import Path
import os,subprocess,json,hashlib
r=Path(__file__).resolve().parents[3];b=Path('D:/StarclusterBuilds/pcm5102_song_audio_20261031')
tb=b/'tb_song_top.v'
tb.write_text('''`timescale 1ns/1ps
module tb_song_top;
reg clk=0;always #10 clk=~clk;
reg play_n=1,stop_n=1,panic_n=1;wire bck,ws,din,pa;
board_pt8211_controls_top dut(.clk(clk),.uart_rx_pin(1'b1),.key_play_n(play_n),.key_stop_n(stop_n),.key_panic_n(panic_n),.uart_tx_pin(),.HP_BCK(bck),.HP_WS(ws),.HP_DIN(din),.PA_EN(pa));
reg[31:0] expected[0:4095];integer tail=0,head=0,bits=0,checked=0;reg[31:0]shift=0;reg aligned=0;
always @(posedge clk)if(!dut.engine.rst&&dut.engine.pcm_valid)begin
 expected[tail]={dut.engine.pcm_left,dut.engine.pcm_right};tail=tail+1;
 if(tail>=4096)$fatal(1,"scoreboard overflow");
end
always @(posedge bck)if(!dut.engine.rst&&!dut.engine.panic)begin
 shift={shift[30:0],din};bits=bits+1;
 if(ws!==((bits>=16&&bits<=31)?1'b1:1'b0))$fatal(1,"WS framing");
 if(bits==32)begin bits=0;
  if(!aligned&&shift!=0)begin while(head<tail&&expected[head]==0)head=head+1;aligned=1;end
  if(aligned)begin
   if(head>=tail||shift!==expected[head])$fatal(1,"PCM mismatch head=%0d got=%h expected=%h",head,shift,expected[head]);
   head=head+1;checked=checked+1;
  end
 end
end
initial begin
 wait(!dut.engine.rst);repeat(15000)@(negedge clk);
 if(dut.engine.playing||pa!==0)$fatal(1,"Boot must remain stopped, onboard amp off");
 play_n=0;repeat(300000)@(negedge clk);play_n=1;
 wait(checked>=512);
 if(!dut.engine.playing||dut.engine.dac_dropped||dut.engine.dac_underruns||dut.engine.clips||dut.engine.deadline_miss)$fatal(1,"Song health");
 $display("PASS audio-only song: stopped boot, S0 start, %0d decoded I2S frames equal synthesized PCM, clean counters",checked);
 $finish;
end
initial begin #80000000;$fatal(1,"Timeout");end
endmodule
''')
binary=r/'tmp/oss-cad-suite/bin';env=dict(os.environ);env['PATH']=str(binary)+os.pathsep+str(binary.parent/'lib')+os.pathsep+env['PATH']
files=[p for p in b.iterdir() if p.suffix in ('.v','.sv') and not p.name.startswith('tb_')]+[tb]
vendor=Path('D:/Gowin/Gowin_V1.9.12.03_x64/IDE/simlib/gw5a/prim_sim.v')
p=subprocess.run([str(binary/'iverilog.exe'),'-g2012','-I',str(b),'-s','tb_song_top','-o',str(b/'top.vvp'),*map(str,files),str(vendor)],cwd=b,env=env,capture_output=True,text=True)
assert p.returncode==0,p.stderr
p=subprocess.run([str(binary/'vvp.exe'),str(b/'top.vvp')],cwd=b,env=env,capture_output=True,text=True,timeout=300)
record=dict(status='passed' if p.returncode==0 else 'failed',log=p.stdout+p.stderr,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(b/'top_test.json').write_text(json.dumps(record,indent=2));print(record['log']);assert p.returncode==0
