`timescale 1ns/1ps
module tb_uart;
reg clk=0,rst=1,start=0;
reg [7:0] data;
wire tx,busy,valid;
wire [7:0] received;
always #10 clk=~clk;
uart_tx #(.DIV(16)) a(clk,rst,data,start,tx,busy);
uart_rx #(.DIV(16)) b(clk,rst,tx,received,valid);
integer i,count=0;
always @(posedge clk) if(valid) begin
    if(received!==data) begin $display("FAIL UART data %h %h",received,data);$finish;end
    count=count+1;
end
initial begin
    repeat(4) @(negedge clk);rst=0;
    for(i=0;i<256;i=i+1) begin
        @(negedge clk);data=i;start=1;@(negedge clk);start=0;
        repeat(170) @(negedge clk);
    end
    if(count!=256) begin $display("FAIL UART count %d",count);$finish;end
    $display("PASS UART: all 256 byte values, 8N1 loopback");$finish;
end
endmodule
