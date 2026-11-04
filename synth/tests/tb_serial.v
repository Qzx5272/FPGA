`timescale 1ns/1ps
module tb_serial;
reg clk=0,rst=1;
always #10 clk=~clk;
wire bck,ws,din,tick,ibck,iws,idin,itick;
audio_serial #(.MODE_I2S(0)) pt(clk,rst,16'h1234,16'hfedc,bck,ws,din,tick);
audio_serial #(.MODE_I2S(1)) is(clk,rst,16'h1234,16'hfedc,ibck,iws,idin,itick);
integer bitcount=0,words=0,samples=0;
reg [15:0] shift=0,ishift=0;
integer ibit=0;
reg previous_ws=0; // Ignore the startup partial I2S word; sync at the first full boundary.
integer good_i2s=0;
always @(posedge bck) if(!rst) begin
    shift={shift[14:0],din};
    if(bitcount==15) begin
        if(shift !== (ws?16'h1234:16'hfedc)) begin $display("FAIL PT8211 word %h ws %b",shift,ws);$finish;end
        words=words+1;bitcount=0;
    end else bitcount=bitcount+1;
end
// Independently track I2S WS transition, then MSB one rising edge later.
reg channel=0;
reg synced=0;
always @(posedge ibck) if(!rst) begin
    if(synced) begin
        ishift={ishift[14:0],idin};
        if(ibit==15) begin
            if(ishift !== (channel?16'hfedc:16'h1234)) begin $display("FAIL I2S %h ch %b",ishift,channel);$finish;end
            good_i2s=good_i2s+1;ibit=0;
        end else ibit=ibit+1;
    end
    if(iws!=previous_ws) begin channel=iws;synced=1;ibit=0; end
    previous_ws=iws;
end
always @(posedge tick) samples=samples+1;
initial begin
    repeat(4) @(negedge clk); rst=0;
    repeat(500000) @(negedge clk); // exactly 10 ms of system clocks
    if(samples<479 || samples>481 || words<950 || good_i2s<949) begin
        $display("FAIL sample rate/count %d %d %d",samples,words,good_i2s);$finish;end
    $display("PASS audio: PT8211 and standard I2S, independent L/R, 48 kHz");$finish;
end
endmodule
