`timescale 1ns/1ps
// Behavioral clock only; vendor PLL, IO and analog audio require board tests.
module gowin_audio_clock(input clk50,resetn,output reg audio_clk=0,output reg locked=0);
 always #20.344827586 audio_clk=~audio_clk;
 always @(posedge clk50) locked<=resetn;
endmodule
module tb;
 reg clk=0;always #10 clk=~clk;
 reg kp=1,ks=1,km=1;
 wire bck,ws,sd,pa,mbck,mws_pin;
 reg mic_sd=0;
 audio_bringup_top #(.DEBOUNCE_CYCLES(8),.MIC_WARMUP_FRAMES(32)) dut(clk,kp,ks,km,mic_sd,bck,ws,sd,pa,mbck,mws_pin);
 reg [23:0] microphone=24'h010000;
 integer mslot=0,dslot=0,frames=0,nonzero=0;
 reg mws=1,dws=0,saw_right=0,synced=0;
 reg [23:0] word=0,lword=0;
 integer check_mode=-1;
 reg [23:0] expected=0;
 always @(posedge dut.rst) begin mslot=0;mws=1;dslot=0;dws=0;saw_right=0;synced=0;end
 always @(negedge mbck) if(!dut.rst) begin
  #1;
  if(mws_pin!=mws)begin mslot=0;mws=mws_pin;end else mslot=mslot+1;
  if(!mws_pin && mslot>=1 && mslot<=24) mic_sd<=#69 microphone[24-mslot];
  else mic_sd<=#69 0;
 end
 always @(posedge bck) if(!dut.rst) begin
  if(mbck!==bck||mws_pin!==ws)$fatal(1,"separate clock ports lost coherence");
  if(ws)saw_right=1;
  if(saw_right&&!ws&&dws)synced=1;
  if(ws!=dws) begin dslot=0;dws=ws;end else dslot=dslot+1;
  if(dslot>=1&&dslot<=24)word={word[22:0],sd};
  if(synced&&dslot==24)begin
   if(!ws)lword=word;
   else begin
    frames=frames+1;
    if(lword!==word)$fatal(1,"monitor is not dual mono");
    if(word!=0)nonzero=nonzero+1;
    if(check_mode==0&&word!==expected)$fatal(1,"expected %h got %h",expected,word);
    if(pa!==0)$fatal(1,"onboard amplifier enabled");
   end
  end
 end
 task waitframes(input integer n);integer target;begin target=frames+n;wait(frames>=target);end endtask
 task key(input integer n);begin
  check_mode=-1;
  if(n==0)kp=0;else if(n==1)ks=0;else km=0;
  repeat(30)@(negedge dut.audio_clk);
  kp=1;ks=1;km=1;waitframes(5);
 end endtask
 initial begin
  wait(!dut.rst);expected=0;check_mode=0;waitframes(5);
  // Monitoring selected before warmup must remain silent.
  key(1);expected=0;check_mode=0;waitframes(5);check_mode=-1;
  waitframes(30);expected=24'h040000;check_mode=0;waitframes(12);
  check_mode=-1;microphone=24'h400000;waitframes(5);
  expected=24'h7fffff;check_mode=0;waitframes(12);
  check_mode=-1;microphone=24'hc00000;waitframes(5);
  expected=24'h800000;check_mode=0;waitframes(12);
  key(2);expected=0;check_mode=0;waitframes(12);
  key(0);nonzero=0;waitframes(50);if(nonzero<40)$fatal(1,"test tone absent");
  key(2);expected=0;check_mode=0;waitframes(8);
  key(0);waitframes(5);check_mode=-1;
  force dut.locked=0;repeat(10)@(negedge dut.audio_clk);
  if(bck!==0||ws!==0||sd!==0)$fatal(1,"PLL loss did not reset audio");
  release dut.locked;wait(!dut.rst);expected=0;check_mode=0;waitframes(12);
  $display("PASS board modes: mute startup, warmup silence, microphone4x, positive/negative saturation, tone, panic mute, PLL loss/relock mute, amplifier off");$finish;
 end
 initial begin #5000000;$fatal(1,"timeout");end
endmodule
