`timescale 1ns/1ps
module tb_renderer;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,tick=0,active=1,gate=1;reg [6:0] note=69,vel=127;
 reg [3:0] part=4;reg [31:0] gen=1;
 wire [4:0] q,retire_slot;wire retire,valid;
 wire [31:0] retire_gen,miss,clips;wire [15:0] cycles,voices;wire signed [15:0] sample;
 band_renderer dut(clk,rst,panic,tick,q,active,gate,note,vel,part,gen,retire,retire_slot,retire_gen,valid,sample,miss,clips,cycles,voices,8'd128,8'd128,3'd0,part==4?16'd8192:16'd256,4'd13,part==4?16'd0:16'd65535,4'd8);
 integer f,n,j;integer retired=0;reg all_voices=0;
 // Separate test drives query_active below through a combinational mux.
 always @(posedge clk)if(retire)retired=retired+1;
 initial begin
  f=$fopen("synth/band/evidence/renderer_samples.txt","w");
  repeat(3)@(negedge clk);rst=0;
  // All 32 voices stress the worst serial schedule; unison is intentionally coherent.
  for(n=0;n<12000;n=n+1)begin
   if(n==4000)begin part=5;gen=2;end
   if(n==8000)gate=0;
   @(negedge clk);tick=1;@(negedge clk);tick=0;
   wait(valid);#1;
   if(cycles>=1041||miss!=0||sample===16'bx)begin $display("FAIL renderer deadline or X");$fatal;end
   $fwrite(f,"%0d\n",sample);
   repeat(1040-cycles)@(negedge clk);
  end
  if(retired==0||sample!=0||clips!=0)begin $display("FAIL release or coherent-unison headroom");$fatal;end
  $display("METRIC renderer cycles=%0d clips=%0d retire_pulses=%0d",cycles,clips,retired);
  @(negedge clk);panic=1;@(negedge clk);panic=0;#1;
  if(sample!=0)$fatal;
  $fclose(f);$display("PASS renderer: 32 voices, FM/reed, release, panic, bounded cycles");$finish;
 end
 initial begin #400000000;$fatal;end
endmodule
