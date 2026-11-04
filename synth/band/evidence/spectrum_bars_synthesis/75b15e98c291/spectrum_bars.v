// Display-side consumer of spectrum_snapshot, in the same display clock domain.
// 2048-point FFT at 48kHz: positive bins1..1023, 32 quasi-log frequency bands.
// Height is a coarse log amplitude indication, NOT calibrated dB/SPL.
// Caller supplies pixel coordinates/frame_start; no sync generator or HDMI PHY.
module spectrum_bars(
 input clk,rst,frame_start,input[9:0]pixel_x,pixel_y,
 input frame_available,read_valid,input signed[15:0]read_real,read_imag,
 output wire read_enable,output reg[10:0]read_address,output reg release_frame,
 output reg[23:0]rgb,output reg display_valid,output reg[31:0]displayed_frames
);
 localparam IDLE=0,REQUEST=1,WAIT_DATA=2;
 reg[1:0]state;reg[4:0]band;reg[15:0]peak;
 reg front,pending;reg[7:0]bars0[0:31],bars1[0:31];
 wire[15:0]ar=read_real[15]?(~read_real+16'd1):read_real;
 wire[15:0]ai=read_imag[15]?(~read_imag+16'd1):read_imag;
 wire[16:0]sum={1'b0,ar}+{1'b0,ai};
 wire[15:0]magnitude=sum[16]?16'hffff:sum[15:0];
 wire[15:0]next_peak=magnitude>peak?magnitude:peak;
 assign read_enable=state==REQUEST&&frame_available&&!rst;
 function[10:0]band_end(input[4:0]b);
  begin case(b)
   0:band_end=1;1:band_end=2;2:band_end=3;3:band_end=4;
   4:band_end=5;5:band_end=6;6:band_end=7;7:band_end=9;
   8:band_end=11;9:band_end=14;10:band_end=17;11:band_end=21;
   12:band_end=26;13:band_end=32;14:band_end=39;15:band_end=48;
   16:band_end=59;17:band_end=72;18:band_end=88;19:band_end=108;
   20:band_end=132;21:band_end=161;22:band_end=197;23:band_end=241;
   24:band_end=294;25:band_end=359;26:band_end=438;27:band_end=535;
   28:band_end=653;29:band_end=797;30:band_end=923;default:band_end=1023;
  endcase end
 endfunction
 function[7:0]height(input[15:0]v);
  integer bitno;begin height=0;
   for(bitno=0;bitno<16;bitno=bitno+1)if(v[bitno])height=(bitno+1)*15;
  end
 endfunction
 integer i;
 always @(posedge clk or posedge rst)begin
  if(rst)begin
   state<=IDLE;band<=0;peak<=0;read_address<=1;release_frame<=0;
   front<=0;pending<=0;display_valid<=0;displayed_frames<=0;
   for(i=0;i<32;i=i+1)begin bars0[i]<=0;bars1[i]<=0;end
  end else begin
   release_frame<=0;
   if(frame_start&&pending)begin
    front<=!front;pending<=0;display_valid<=1;
    displayed_frames<=displayed_frames+1'b1;
   end
   case(state)
    IDLE:if(frame_available&&!pending)begin
     read_address<=1;band<=0;peak<=0;state<=REQUEST;
    end
    REQUEST:if(frame_available)state<=WAIT_DATA;else state<=IDLE;
    WAIT_DATA:if(!frame_available)state<=IDLE;
     else if(read_valid)begin
      if(read_address==band_end(band))begin
       if(front)bars0[band]<=height(next_peak);else bars1[band]<=height(next_peak);
       peak<=0;band<=band+1'b1;
      end else peak<=next_peak;
      if(read_address==1023)begin pending<=1;release_frame<=1;state<=IDLE;end
      else begin read_address<=read_address+1'b1;state<=REQUEST;end
     end
    default:state<=IDLE;
   endcase
  end
 end
 wire[9:0]x_relative=pixel_x-10'd64;
 wire[4:0]column=x_relative[8:4];
 wire[7:0]visible_height=front?bars1[column]:bars0[column];
 always @*begin
  rgb=24'h080c16;
  if(pixel_x>=64&&pixel_x<576&&pixel_y>=200&&pixel_y<440)begin
   if(display_valid&&x_relative[3:0]<14&&pixel_y>=440-visible_height)
    rgb=visible_height>=210?24'hff9e40:24'h35d8c2;
  end
 end
endmodule
