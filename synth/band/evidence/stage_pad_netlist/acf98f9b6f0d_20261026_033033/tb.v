`timescale 1ns/1ps
module tb_pads;
 reg clk=0;always #10 clk=~clk;
 reg rst=1,panic=0,sv=0,ready=0;reg [2:0] ch=0;reg [119:0] samples=0;
 reg cfg=0,inv=0;reg[11:0]base=0;reg[15:0]gain=127;integer n,expected;
 wire valid,off,exhausted;wire [6:0] contact,pressure;wire [31:0] serial,overruns;wire [559:0] values;
 stage_pad_reference dut(clk,rst,panic,sv,ch,samples,cfg,7'd0,base,gain,inv,7'd24,7'd12,valid,ready,off,contact,pressure,serial,values,overruns,exhausted);

 GSR GSR(.GSRI(1'b1));
 wire nvalid,noff,nexhausted;wire[6:0]ncontact,npressure;
 wire[31:0]nserial,noverruns;wire[559:0]nvalues;
 stage_pad_frontend netlist(clk,rst,panic,sv,ch,samples,cfg,7'd0,base,gain,inv,
  7'd24,7'd12,nvalid,ready,noff,ncontact,npressure,nserial,nvalues,noverruns,nexhausted);
 integer compared=0;
 always @(negedge clk)begin
  #1;
  if(!rst)begin
   compared=compared+1;
   if({nvalid,nvalues,noverruns,nexhausted}!=={valid,values,overruns,exhausted})
    $fatal(1,"vendor pad outputs differ cycle=%0d",compared);
   if(valid&&{noff,ncontact,npressure,nserial}!=={off,contact,pressure,serial})
    $fatal(1,"vendor pad event differs cycle=%0d",compared);
  end
 end

 task frame;input [2:0] c;input [11:0] a,b;
 begin @(negedge clk);ch=c;samples={b,a};sv=1;@(negedge clk);sv=0;wait(!dut.busy);repeat(3)@(negedge clk);end endtask
 task accept;input o;input [6:0] c;input [31:0] s;
 begin wait(valid);#1;if(off!=o||contact!=c||serial!=s)begin $display("FAIL pad event off=%b contact=%d serial=%d",off,contact,serial);$fatal;end
  @(negedge clk);ready=1;@(negedge clk);ready=0;end endtask
 initial begin
  repeat(3)@(negedge clk);rst=0;
  frame(0,0,0);frame(0,2000,0);accept(0,0,1);
  frame(0,0,0);frame(0,2500,0); // old release must precede the new contact generation
  accept(1,0,1);accept(0,0,2);
  frame(0,0,2000);accept(1,0,2);accept(0,8,1);
  panic=1;@(negedge clk);panic=0;
  frame(0,0,2000);if(valid)$fatal; // held pad must not retrigger after panic
  frame(0,0,0);frame(0,0,3000);accept(0,8,2);
  if(overruns!=0||exhausted)$fatal;
  // Compare clamp/subtract/multiply including inverted and saturated inputs.
  for(n=0;n<256;n=n+1)begin
   @(negedge clk);cfg=1;base=(n*79)%4096;gain=(n*997)%65536;inv=n%2;
   @(negedge clk);cfg=0;
   expected=inv?4095-(n*37)%4096:(n*37)%4096;
   expected=expected>base?expected-base:0;
   expected=(expected*gain)>>12;if(expected>127)expected=127;
   frame(0,(n*37)%4096,0);
   if(values[6:0]!==expected)$fatal(1,"numeric mismatch n=%d got=%d expected=%d",n,values[6:0],expected);
  end
  // Configuration captured at lookup stays coherent through later phases.
  @(negedge clk);cfg=1;base=100;gain=4096;inv=0;
  @(negedge clk);cfg=0;sv=1;samples=150;
  @(negedge clk);sv=0;
  @(negedge clk);cfg=1;base=4000;gain=65535;inv=1;
  @(negedge clk);cfg=0;wait(!dut.busy);#1;
  if(values[6:0]!=50)$fatal(1,"mixed calibration generations");
  // A busy input is counted, not allowed to corrupt the in-flight batch.
  @(negedge clk);sv=1;samples=0;@(negedge clk);sv=0;
  @(negedge clk);sv=1;@(negedge clk);sv=0;wait(!dut.busy);#1;
  if(overruns!=1)$fatal(1,"busy batch was not rejected");
  @(negedge clk);sv=1;@(negedge clk);sv=0;
  repeat(2)@(negedge clk);panic=1;@(negedge clk);panic=0;
  if(dut.busy||valid||dut.physical)$fatal(1,"panic did not cancel pipeline");
  frame(0,150,0);
  if(values[6:0]!=0)$fatal(1,"panic discarded calibration");
  // Reset must invalidate old RAM contents and restore logical defaults.
  @(negedge clk);rst=1;repeat(2)@(negedge clk);rst=0;
  frame(0,4095,0);
  if(values[6:0]!=126)$fatal(1,"reset did not restore default calibration");
  $display("PASS vendor-pad equivalence: calibration scaling, hysteresis, release priority, identities, panic inhibit");$finish;
 end
 initial begin #1000000;$fatal;end
endmodule
