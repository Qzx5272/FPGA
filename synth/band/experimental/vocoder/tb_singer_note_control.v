`timescale 1ns/1ps
module tb;
reg clk=0;always #10 clk=~clk;
reg rst=1,panic=0,event_valid=0;wire event_ready,gate;wire[6:0]note,velocity;
reg[1:0]event_kind=0;reg[7:0]event_source=1,event_contact=0;
reg[3:0]event_part=15;reg[31:0]event_epoch=1,event_serial=0;
reg[6:0]event_note=60,event_velocity=100;wire[31:0]rejected,stale_off,duplicates;
singer_note_control dut(.*);
task event_send;
 input[1:0]kind;input[7:0]source,contact;input[31:0]epoch,serial;input[6:0]pitch;
 begin
  @(negedge clk);event_kind=kind;event_source=source;event_contact=contact;
  event_epoch=epoch;event_serial=serial;event_note=pitch;event_valid=1;
  while(!event_ready)@(negedge clk);
  @(negedge clk);event_valid=0;repeat(70)@(negedge clk);
 end
endtask
initial begin
 repeat(4)@(negedge clk);rst=0;
 event_send(0,1,0,1,1,60);if(!gate||note!=60)$fatal(1,"first note");
 event_send(0,2,1,1,2,67);if(!gate||note!=67)$fatal(1,"last note priority");
 event_send(1,2,1,0,2,67);if(!gate||note!=67||stale_off!=1)$fatal(1,"old epoch off");
 event_send(1,2,1,1,2,67);if(!gate||note!=60)$fatal(1,"fallback held note");
 event_send(0,1,0,1,1,60);if(duplicates!=1||note!=60)$fatal(1,"duplicate");
 event_send(0,2,1,2,3,72);if(note!=72)$fatal(1,"new generation");
 event_send(1,2,1,1,2,67);if(note!=72||!gate||stale_off!=2)$fatal(1,"old off kills new note");
 event_send(2,2,0,0,0,0);if(note!=60||!gate)$fatal(1,"lost source fallback");
 event_send(3,0,0,0,0,0);if(gate)$fatal(1,"ownership release");
 event_part=7;event_send(0,1,0,1,9,80);if(gate)$fatal(1,"choir must not feed singer");
 event_part=15;event_send(0,1,0,1,10,80);if(!gate)$fatal(1,"rejoin");
 panic=1;@(negedge clk);if(gate)$fatal(1,"panic");panic=0;
 repeat(70)@(negedge clk);if(gate)$fatal(1,"stale note after panic");
 $display("PASS singer identity,latest-note,fallback,old releases,source loss,part separation,panic");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
