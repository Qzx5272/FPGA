`timescale 1ns/1ps
`include "song_config.vh"
module tb_store;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,abort_upload=0,activate=0,uv=0;reg [11:0] read_address=0;
 reg [2:0] cmd=0;reg [31:0] idx=0,value=0,aux=0;
 wire [95:0] data;wire [12:0] count,received;wire [31:0] duration,errors;
 wire ready,pending,uploading;wire [1:0] expected;
 reg [31:0] fixture[0:6];integer i;
 song_store dut(clk,rst,abort_upload,activate,read_address,data,count,duration,uv,ready,cmd,idx,value,aux,pending,uploading,received,expected,errors);
 task send;input [2:0] c;input [31:0] a,v,x;
 begin wait(ready);@(negedge clk);cmd=c;idx=a;value=v;aux=x;uv=1;@(negedge clk);uv=0;wait(ready);@(negedge clk);end endtask
 initial begin
  $readmemh("synth/band/assets/store_fixture.hex",fixture);
  repeat(3)@(negedge clk);rst=0;repeat(3)@(negedge clk);
  send(3,2,1000,fixture[6]);
  for(i=0;i<6;i=i+1)send(i%3,i/3,fixture[i],0);
  send(4,0,0,0);if(!pending||count!=`SONG_EVENTS||errors!=0)$fatal;
  activate=1;@(negedge clk);activate=0;repeat(3)@(negedge clk);
  if(count!=2||duration!=1000||data!={fixture[2],fixture[1],fixture[0]})$fatal;
  read_address=1;repeat(3)@(negedge clk);if(data!={fixture[5],fixture[4],fixture[3]})$fatal;
  send(3,2,1000,32'd1);for(i=0;i<6;i=i+1)send(i%3,i/3,fixture[i],0);
  send(4,0,0,0);if(pending||errors!=1||count!=2)$fatal;
  send(3,2,1000,fixture[6]);send(1,0,123,0);if(uploading||errors!=2)$fatal;
  activate=1;@(negedge clk);activate=0;repeat(3)@(negedge clk);if(data!={fixture[5],fixture[4],fixture[3]})$fatal;
  $display("PASS score storage: atomic banks, ordered upload, Python CRC32, corrupt/incomplete retention");$finish;
 end
 initial begin #100000;$fatal;end
endmodule
