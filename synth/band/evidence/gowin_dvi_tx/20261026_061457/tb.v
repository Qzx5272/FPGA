`timescale 1ns/1ps
module tb;
reg pc=0,sc=0;always #20 pc=~pc;always #4 sc=~sc;
reg[27:0]s=0;reg[27:0]stimulus[0:1199];integer i,fd,n=0;
wire cp,cn;wire[2:0]dp,dn;
GSR GSR(.GSRI(1'b1));
gowin_dvi_tx dut(pc,sc,s[27],s[26],s[25],s[24],s[23:0],cp,cn,dp,dn);
always @(posedge sc or negedge sc)begin
 #1;if(cp!==pc||cn!==!pc||dn!==~dp)$fatal(1,"differential pins or clock polarity");
 $fdisplay(fd,"%0d %b",n,dp);n=n+1;
end
initial begin
fd=$fopen("serial.txt","w");$readmemh("stimulus.hex",stimulus);
for(i=0;i<1200;i=i+1)begin @(negedge pc);s=stimulus[i];end
repeat(16)@(negedge pc);$fclose(fd);$finish;
end
endmodule
