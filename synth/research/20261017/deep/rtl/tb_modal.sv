`timescale 1ns/1ps
module tb_modal;
reg clk=0;always #10 clk=~clk;
reg rst=1,valid_in=0;
reg signed [35:0] x=0,y=0,drive=0;
reg signed [23:0] a=0,b=0;
wire valid_out,saturated;wire signed [35:0] next_x,next_y;
modal_rotation dut(.*);
reg signed [35:0] ex,ey;integer es;
reg signed [35:0] ox[0:2],oy[0:2];reg os[0:2];reg [2:0] vv=0;
integer fd,rc,i=0,count=0,satcount=0;
always @(posedge clk)begin
 ox[2]=ox[1];ox[1]=ox[0];ox[0]=ex;
 oy[2]=oy[1];oy[1]=oy[0];oy[0]=ey;
 os[2]=os[1];os[1]=os[0];os[0]=es;
 if(rst)vv=0;else vv={vv[1:0],valid_in};
 #1;
 if(valid_out!==vv[2])$fatal(1,"modal valid mismatch");
 if(valid_out)begin
   if(next_x!==ox[2] || next_y!==oy[2] || saturated!==os[2])
     $fatal(1,"modal arithmetic mismatch %0d %0d / %0d %0d",next_x,next_y,ox[2],oy[2]);
   count=count+1;if(saturated)satcount=satcount+1;
 end
end
initial begin
 ex=0;ey=0;es=0;repeat(4)@(negedge clk);rst=0;
 fd=$fopen("modal_vectors.txt","r");if(!fd)$fatal(1,"missing vectors");
 while(!$feof(fd))begin
  @(negedge clk);rc=$fscanf(fd,"%d %d %d %d %d %d %d %d\n",x,y,drive,a,b,ex,ey,es);
  valid_in=(rc==8 && i%11!=0);rst=(i%1009==1008);i=i+1;
 end
 @(negedge clk);valid_in=0;rst=0;repeat(6)@(negedge clk);
 $display("PASS modal signed arithmetic, rounding, saturation, valid/reset: %0d outputs, %0d saturated",count,satcount);$finish;
end
endmodule
