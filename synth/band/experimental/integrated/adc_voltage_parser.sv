// Observed COM9 protocol: 460800 8N1, <v>:d.ddd,... x10, LF, 20 frames/s.
// Atomic frame commit; malformed, out-of-range and incomplete frames never publish.
module adc_voltage_parser #(parameter TIMEOUT=25000000)(input clk,rst,input[7:0]data,input valid,
 output reg update,output reg[119:0]millivolts,output wire online,output reg[31:0]errors);
 reg[3:0]state,channel;reg[11:0]value;reg[119:0]pending;reg[25:0]age;
 assign online=age<TIMEOUT;
 wire digit=data>=48&&data<=57;
 always @(posedge clk)begin
  if(rst)begin state<=0;channel<=0;value<=0;pending<=0;millivolts<=0;update<=0;errors<=0;age<=TIMEOUT;end
  else begin
   update<=0;if(age<TIMEOUT)age<=age+1'b1;
   if(valid)begin
    if(data==60)state<=1;
    else case(state)
     0:begin end
     1:if(data==118)state<=2;else begin state<=0;errors<=errors+1'b1;end
     2:if(data==62)state<=3;else begin state<=0;errors<=errors+1'b1;end
     3:if(data==58)begin state<=4;channel<=0;end else begin state<=0;errors<=errors+1'b1;end
     4:if(data>=48&&data<=51)begin value<=(data-48)*1000;state<=5;end else begin state<=0;errors<=errors+1'b1;end
     5:if(data==46)state<=6;else begin state<=0;errors<=errors+1'b1;end
     6:if(digit)begin value<=value+(data-48)*100;state<=7;end else begin state<=0;errors<=errors+1'b1;end
     7:if(digit)begin value<=value+(data-48)*10;state<=8;end else begin state<=0;errors<=errors+1'b1;end
     8:if(digit)begin value<=value+(data-48);state<=9;end else begin state<=0;errors<=errors+1'b1;end
     9:begin
      if(value>3300)begin state<=0;errors<=errors+1'b1;end
      else if(channel<9&&data==44)begin pending[channel*12+:12]<=value;channel<=channel+1'b1;state<=4;end
      else if(channel==9&&data==13)state<=10;
      else if(channel==9&&data==10)begin millivolts<={value,pending[107:0]};age<=0;update<=1;state<=0;end
      else begin state<=0;errors<=errors+1'b1;end
     end
     10:if(data==10)begin millivolts<={value,pending[107:0]};age<=0;update<=1;state<=0;end
        else begin state<=0;errors<=errors+1'b1;end
     default:state<=0;
    endcase
   end
  end
 end
endmodule
