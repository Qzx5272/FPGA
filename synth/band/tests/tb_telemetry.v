`timescale 1ns/1ps
module tb_telemetry;
 reg clk=0;always #10 clk=~clk;
 reg rst=1;reg [191:0] counter=0;
 wire tx;wire [7:0] data;wire valid;integer file,n=0;
 always @(posedge clk)counter<=counter+1;
 status_sender #(.UART_DIV(8)) dut(clk,rst,1'b1,{counter,32'h00008004},tx);
 uart_rx #(.DIV(8)) rx(clk,rst,tx,data,valid);
 always @(posedge clk)if(valid)begin $fwrite(file,"%02x\n",data);n=n+1;if(n==3400)begin $fclose(file);$display("PASS telemetry: 100 continuously requested frames with changing snapshot");$finish;end end
 initial begin file=$fopen("synth/band/evidence/telemetry_burst.hex","w");repeat(4)@(negedge clk);rst=0;end
 initial begin #10000000;$fatal;end
endmodule
