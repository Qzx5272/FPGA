`timescale 1ns/1ps
module tb_hq_sine;
  reg clk=0; always #10 clk=~clk;
  reg rst=1,valid_in=0;reg [31:0] phase=0;
  wire valid_out;wire signed [17:0] sample;
`ifdef QUARTER
  hq_sine_quarter dut(.*);
`else
  hq_sine dut(.*);
`endif
  integer i,fd,rc,expected,error,max_error=0,checked=0;
  reg [31:0] input_phase;
  integer oracle[0:3];reg [3:0] want_valid=0;
  always @(posedge clk) begin
    oracle[3]=oracle[2];oracle[2]=oracle[1];oracle[1]=oracle[0];oracle[0]=expected;
    if(rst) want_valid=0; else want_valid={want_valid[2:0],valid_in};
    #1;
    if(valid_out!==want_valid[3]) $fatal(1,"valid/reset alignment failure");
    if(valid_out) begin
      error=$signed(sample)-oracle[3];if(error<0)error=-error;
      if(error>max_error)max_error=error;
      if(error>2)$fatal(1,"analytic sine error %0d > 2 LSB",error);
      checked=checked+1;
    end
  end
  initial begin
    expected=0;
    repeat(4) @(negedge clk);rst=0;
    fd=$fopen("sine_vectors.txt","r");if(!fd)$fatal(1,"vectors missing");
    i=0;
    while(!$feof(fd)) begin
      @(negedge clk);
      rc=$fscanf(fd,"%h %d\n",input_phase,expected);
      if(rc==2) begin phase=input_phase;valid_in=(i%13!=0);rst=(i%10007==10006);i=i+1;end
    end
    @(negedge clk);rst=0;valid_in=0;
    repeat(6) @(negedge clk);
    $display("PASS analytic sine, bubbles, reset: checked=%0d max_error=%0d LSB",checked,max_error);
    $finish;
  end
endmodule
