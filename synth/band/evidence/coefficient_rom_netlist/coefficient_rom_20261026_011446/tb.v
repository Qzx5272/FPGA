`timescale 1ns/1ps
module tb;
 GSR GSR(.GSRI(1'b1));
 reg clk=0;always #10 clk=~clk;reg[4:0]row=0;reg[3:0]column=0;
 wire[31:0]matrix_word,flat_word;reg[31:0]expected[0:169];integer i,matrix_errors=0,flat_errors=0;
 coefficient_rom dut(.*);
 initial begin
  $readmemh("coeffs.mem",expected);repeat(5)@(negedge clk);
  for(i=0;i<170;i=i+1)begin
   row=i/10;column=i%10;repeat(3)@(negedge clk);
   if(matrix_word!==expected[i])begin matrix_errors=matrix_errors+1;$display("MATRIX_MISMATCH index=%0d got=%h expected=%h",i,matrix_word,expected[i]);end
   if(flat_word!==expected[i])begin flat_errors=flat_errors+1;$display("FLAT_MISMATCH index=%0d got=%h expected=%h",i,flat_word,expected[i]);end
  end
  $display("RESULT matrix_errors=%0d flat_errors=%0d",matrix_errors,flat_errors);$finish;
 end
endmodule
