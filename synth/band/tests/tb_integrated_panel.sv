`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1;always #10 clk=~clk;
 reg[5:0]a=0,b=0,sw=63;reg[3:0]keys=0;reg joy=1,au=0,online=0,observed=0,ready=1;
 reg[119:0]mv=0;reg[223:0]op=0;wire valid,play,stop,panic,sustain,rec,replay,song_request;
 wire[223:0]payload;wire[3:0]part,pick,release_rate;wire signed[3:0]octave;
 wire[1:0]page,mic;wire[2:0]song;wire[6:0]expression_value;wire[13:0]attack;
 integer plays=0,stops=0,recs=0,replays=0,packets=0;reg[223:0]captured[0:63];
 panel_integrated #(.DEBOUNCE(3),.ENC_STABLE(2),.LONG_PRESS(50)) dut(
 clk,rst,a,b,sw,keys,joy,au,online,mv,observed,op,valid,ready,payload,
 play,stop,panic,sustain,part,octave,page,mic,rec,replay,song_request,song,pick,expression_value,attack,release_rate);
 always @(posedge clk)if(!rst)begin
  if(play)plays=plays+1;if(stop)stops=stops+1;if(rec)recs=recs+1;if(replay)replays=replays+1;
  if(valid&&ready)begin captured[packets]=payload;packets=packets+1;end
 end
 task settle;begin repeat(12)@(negedge clk);end endtask
 task rotate(input integer n);begin b[n]=1;settle();a[n]=1;settle();b[n]=0;settle();a[n]=0;settle();end endtask
 initial begin
  repeat(5)@(negedge clk);rst=0;settle();if(plays||stops||sustain)$fatal(1,"idle");
  keys=1;settle();settle();if(plays!=1)$fatal(1,"HIGH play edge");keys=0;settle();
  keys=2;settle();keys=0;settle();if(stops!=1)$fatal(1,"HIGH stop");
  joy=0;settle();if(!sustain)$fatal(1,"hold sustain");joy=1;settle();if(sustain)$fatal(1,"release sustain");
  keys=8;settle();keys=0;settle();if(octave!=1)$fatal(1,"octave");
  sw[1]=0;settle();sw[1]=1;settle();if(recs!=1||replays)$fatal(1,"short record");
  sw[1]=0;repeat(80)@(negedge clk);sw[1]=1;settle();if(recs!=1||replays!=1)$fatal(1,"long replay");
  sw[2]=0;repeat(80)@(negedge clk);sw[2]=1;settle();if(mic!=1)$fatal(1,"mic cycle");
  ready=0;rotate(0);rotate(2);rotate(3);if(part!=9)$fatal(1,"selection");
  ready=1;settle();if(packets<2||captured[1][27:24]!=8||captured[1][15:8]!=11)$fatal(1,"queued parameter retargeted");
  online=1;mv=0;mv[71:48]=24'hbb8bb8;au=1;@(negedge clk);au=0;settle();
  if(pick!=0)$fatal(1,"unused AIN4/5 acquired fader");
  for(integer ch=0;ch<4;ch=ch+1)begin
   mv[ch*12+:12]=2990;au=1;@(negedge clk);au=0;settle();
   if(pick!=((1<<(ch+1))-1))$fatal(1,"wrong pickup channel %d",ch);
   if(captured[packets-1][27:24]!=(ch==0?3:ch==1?4:ch==2?6:7)||
      captured[packets-1][198:192]!=127)$fatal(1,"full range/target %d",ch);
  end
  online=0;settle();if(pick)$fatal(1,"offline pickup");
  repeat(2)begin sw[2]=0;repeat(80)@(negedge clk);sw[2]=1;settle();end
  if(mic!=3||part!=4||octave!=0||expression_value!=110)$fatal(1,"lesson preset");
  rotate(2);rotate(3);keys=8;settle();keys=0;settle();
  if(part!=4||octave!=0||expression_value!=110)$fatal(1,"lesson parameters changed");
  sw[0]=0;settle();if(!panic||mic!=0)$fatal(1,"panic");
  $display("PASS active-HIGH buttons, sustain, debounce, short/long presses, pending parameter part identity, fader pickup, offline, panic");$finish;
 end
endmodule
