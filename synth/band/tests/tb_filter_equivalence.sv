`timescale 1ns/1ps
module tb;
 reg clk=0,rst=1,valid=0;always #10 clk=~clk;
 reg signed[31:0]carrier=0,modulator=0;
 wire ra,rb,va,vb;
 wire signed[31:0]ca[15:0],cb[15:0],ea[15:0],eb[15:0];
 filterbank #(.COEFF_WIDTH(22)) newer(clk,rst,valid,carrier,modulator,ca,ea,ra,va);
 filterbank_baseline #(.COEFF_WIDTH(22)) prior(clk,rst,valid,carrier,modulator,cb,eb,rb,vb);
 integer cycles,frames,limit=0;reg signed[31:0]prev_c[15:0],prev_e[15:0];reg received;
 task frame;
 begin
   @(negedge clk);if(!ra||!rb)$fatal(1,"not ready");
   valid=1;@(negedge clk);valid=0;received=0;cycles=0;
   while(!va&&cycles<1040)begin
    if(vb)begin received=1;for(integer k=0;k<16;k++)begin prev_c[k]=cb[k];prev_e[k]=eb[k];end end
    @(negedge clk);cycles++;
   end
   if(!va||!received||cycles>=1040)$fatal(1,"audio deadline");
   for(integer k=0;k<16;k++)if(ca[k]!==prev_c[k]||ea[k]!==prev_e[k]||^ca[k]===1'bx||^ea[k]===1'bx)
      $fatal(1,"band mismatch frame=%d band=%d",frames,k);
   if(cycles>limit)limit=cycles;
 end endtask
 initial begin repeat(6)@(negedge clk);rst=0;
  for(frames=0;frames<256;frames++)begin
   carrier=$random;modulator=$random;
   if(frames==0)begin carrier=0;modulator=0;end
   if(frames==1)modulator=32'h80000000;if(frames==2)modulator=32'h7fffffff;
   frame();
  end
  $display("PASS 256 stereo filter frames, 16 bands bit-exact, maximum %0d clocks",limit);$finish;
 end
endmodule
