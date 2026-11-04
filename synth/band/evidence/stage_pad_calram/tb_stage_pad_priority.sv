`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 // Keep sequential logic reset; inspect combinational selection between edges.
 stage_pad_frontend dut(.clk(clk),.rst(1'b1),.panic(1'b0),.sample_valid(1'b0),
 .sample_channel(3'd0),.samples(120'd0),.config_valid(1'b0),.config_channel(7'd0),
 .config_baseline(12'd0),.config_gain(16'd0),.config_invert(1'b0),
 .on_threshold(7'd24),.off_threshold(7'd12),.event_ready(1'b0));
 integer n,j,expected;reg off,found;reg[31:0]rng=32'hf9712385;
 function automatic[31:0]next_rng(input[31:0]x);
  reg[31:0]t;begin t=x^(x<<13);t=t^(t>>17);next_rng=t^(t<<5);end
 endfunction
 initial begin
  repeat(2)@(negedge clk);
  for(n=0;n<2048;n=n+1)begin
   @(negedge clk);
   for(j=0;j<64;j=j+1)begin
    rng=next_rng(rng);dut.sent[j]=rng[0];dut.physical[j]=rng[1];
    dut.serials[j]=rng;dut.sent_serials[j]=rng[2]?rng:(rng^32'h80000000);
   end
   // Sparse cases cover every encoder boundary, including pad63.
   if(n<128)begin
    dut.sent=0;dut.physical=0;
    if(n<64)dut.physical[n]=1;else dut.sent[n-64]=1;
   end
   found=0;expected=0;off=0;
   for(j=0;j<64;j=j+1)if(!found&&dut.sent[j]&&(!dut.physical[j]||dut.sent_serials[j]!=dut.serials[j]))begin found=1;expected=j;off=1;end
   for(j=0;j<64;j=j+1)if(!found&&!dut.sent[j]&&dut.physical[j])begin found=1;expected=j;off=0;end
   #1;if(dut.found!==found||(found&&(dut.chosen!==expected||dut.chosen_off!==off)))$fatal(1,"priority n=%0d expected=%0d got=%0d",n,expected,dut.chosen);
  end
  $display("PASS2048 complete64-pad priority states:old linear reference,all single-bit positions,release-before-on");$finish;
 end
endmodule
