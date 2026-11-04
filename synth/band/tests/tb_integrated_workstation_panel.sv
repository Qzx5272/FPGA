`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1;always #10 clk=~clk;
 reg[5:0]a=0,b=0,sw=63;reg[3:0]keys=0;reg joy=1,au=0,online=0,observed=0,ready=1;
 reg[119:0]mv=0;reg[223:0]op=0;wire valid,play,stop,panic,sustain,rec,replay,song_request;
 wire[223:0]payload;wire[3:0]part,pick,release_rate;wire signed[3:0]octave;
 wire[1:0]page,mic;wire[2:0]song;wire[6:0]expression_value;wire[13:0]attack;
 reg playing=0;wire audition,seat;wire[27:0]faders;wire[6:0]vibrato;integer loads=0,panics=0;
 integer plays=0,stops=0,recs=0,replays=0,packets=0;reg[223:0]captured[0:63];
 panel_integrated #(.DEBOUNCE(3),.ENC_STABLE(2),.LONG_PRESS(50)) dut(
 clk,rst,a,b,sw,keys,joy,au,online,mv,observed,op,valid,ready,payload,
 play,stop,panic,sustain,part,octave,page,mic,rec,replay,song_request,song,pick,expression_value,attack,release_rate,playing,1'b0,audition,seat,faders,vibrato);
 always @(posedge clk)if(!rst)begin
  if(song_request)loads=loads+1;if(panic)panics=panics+1;
  if(play)plays=plays+1;if(stop)stops=stops+1;if(rec)recs=recs+1;if(replay)replays=replays+1;
  if(valid&&ready)begin captured[packets]=payload;packets=packets+1;end
 end
 task settle;begin repeat(12)@(negedge clk);end endtask
 task rotate(input integer n);begin b[n]=1;settle();a[n]=1;settle();b[n]=0;settle();a[n]=0;settle();end endtask
 task press(input integer n,cycles);begin sw[n]=0;repeat(cycles)@(negedge clk);sw[n]=1;settle();end endtask
 task update;begin @(negedge clk);au=1;@(negedge clk);au=0;settle();end endtask
 initial begin
  repeat(5)@(negedge clk);rst=0;settle();if(plays||stops||sustain)$fatal(1,"idle");
  keys=1;settle();settle();if(loads!=1)$fatal(1,"HIGH play edge");keys=0;settle();
  keys=2;settle();keys=0;settle();if(stops!=1)$fatal(1,"HIGH stop");
  joy=0;settle();if(!sustain)$fatal(1,"hold sustain");joy=1;settle();if(sustain)$fatal(1,"release sustain");
  keys=8;settle();keys=0;settle();if(octave!=1)$fatal(1,"octave");
  press(1,12);if(loads!=2)$fatal(1,"play");playing=1;press(1,12);playing=0;if(stops!=2)$fatal(1,"stop");
  press(1,80);if(loads!=2||dut.tempo!=120)$fatal(1,"long press double fired");
  press(2,12);if(page!=1)$fatal(1,"next page");press(2,80);if(page!=0)$fatal(1,"home");
  press(3,12);if(!audition||loads!=3)$fatal(1,"solo");
  press(4,12);if(song!=4||loads!=3||page!=3)$fatal(1,"browse previous without play");
  press(5,12);if(song!=0||loads!=3)$fatal(1,"browse next");
  press(5,80);if(!seat||song!=0||part!=4)$fatal(1,"take selected playable part");
  press(4,80);if(mic!=1)$fatal(1,"microphone");
  press(0,12);if(replays!=1)$fatal(1,"replay on song page");
  press(2,80);press(0,12);press(0,80);if(recs!=1||panics!=1)$fatal(1,"record or panic");
  online=1;mv={10{12'd0}};mv[59:48]=1650;mv[71:60]=1650;update();
  mv[59:48]=3100;mv[71:60]=3100;update();update();
  if(octave!=2||vibrato<100)$fatal(1,"joystick repeated or no vibrato");
  mv[59:48]=1650;update();mv[59:48]=100;update();if(octave!=1)$fatal(1,"joystick left");
  for(integer ch=0;ch<4;ch=ch+1)begin mv[12*ch+:12]=3100;update();if(!pick[ch]||faders[7*ch+:7]!=127)$fatal(1,"pickup %d",ch);end
  press(3,80);if(mic!=3||part!=4||seat||octave!=0||vibrato!=0||pick!=0)$fatal(1,"lesson preset");
  rotate(3);update();if(part!=4||faders!={7'd24,7'd64,7'd64,7'd64})$fatal(1,"lesson lock");
  press(3,80);if(mic!=0)$fatal(1,"exit lesson");
  op=0;op[23:16]=3;op[15:8]=23;op[27:24]=3;op[63:56]=4;op[223:192]=1;
  @(negedge clk);observed=1;@(negedge clk);observed=0;settle();
  if(!seat||audition||song!=1||part!=3||mic!=0)$fatal(1,"phone ensemble");
  op[63:56]=3;@(negedge clk);observed=1;@(negedge clk);observed=0;settle();
  if(seat||audition||mic!=3||page!=3)$fatal(1,"phone guided");
  $display("PASS six push encoders, reserved buttons, four faders, joystick and study lock");$finish;
 end
endmodule
