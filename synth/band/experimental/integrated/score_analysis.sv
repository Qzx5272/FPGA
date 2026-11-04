module score_analysis(
 input clk,rst,valid,input signed[15:0]left,right,
 output reg[127:0]spectrum,output reg[383:0]trace_l,trace_r,
 output reg[5:0]peak_l,peak_r
);
 wire ready;wire[10:0]bin;wire signed[15:0]re,im;
 pcm_spectrum fft(.audio_clk(clk),.analysis_clk(clk),.rst(rst),.pcm_valid(valid),
  .pcm_left(left),.pcm_right(right),.spectrum_valid(ready),.spectrum_ready(1'b1),
  .spectrum_bin(bin),.spectrum_real(re),.spectrum_imag(im));
 function[10:0]band_end(input[4:0]b);begin case(b)
  0:band_end=1;1:band_end=2;2:band_end=3;3:band_end=4;4:band_end=5;5:band_end=6;
  6:band_end=7;7:band_end=9;8:band_end=11;9:band_end=14;10:band_end=17;11:band_end=21;
  12:band_end=26;13:band_end=32;14:band_end=39;15:band_end=48;16:band_end=59;
  17:band_end=72;18:band_end=88;19:band_end=108;20:band_end=132;21:band_end=161;
  22:band_end=197;23:band_end=241;24:band_end=294;25:band_end=359;26:band_end=438;
  27:band_end=535;28:band_end=653;29:band_end=797;30:band_end=923;default:band_end=1023;
 endcase end endfunction
 reg[4:0]band;reg[15:0]largest;reg[127:0]work;
 wire[15:0]mr=re[15]?-re:re,mi=im[15]?-im:im;
 wire[15:0]mag=mr>mi?mr:mi;wire[15:0]maximum=mag>largest?mag:largest;
 function[3:0]logamp(input[15:0]v);integer j;begin logamp=0;for(j=0;j<16;j=j+1)if(v[j])logamp=j;end endfunction
 function[5:0]point(input signed[15:0]v);begin
  point=v>7935?63:v< -8192?0:6'd32+v[13:8];
 end endfunction
 reg[9:0]meter_count;reg[15:0]ml,mr_peak;
 wire[15:0]al=left[15]?-left:left,ar=right[15]?-right:right;
 always @(posedge clk)begin
  if(rst)begin band<=0;largest<=0;work<=0;spectrum<=0;trace_l<=0;trace_r<=0;peak_l<=0;peak_r<=0;meter_count<=0;ml<=0;mr_peak<=0;end
  else begin
   if(ready)begin
    if(bin==0)begin largest<=0;band<=0;end
    else if(bin<=1023)begin
     if(bin==band_end(band))begin
      work[band*4+:4]<=logamp(maximum);largest<=0;band<=band+1'b1;
      if(bin==1023)spectrum<={logamp(maximum),work[123:0]};
     end else largest<=maximum;
    end
   end
   if(valid)begin
    trace_l<={trace_l[377:0],point(left)};trace_r<={trace_r[377:0],point(right)};
    meter_count<=meter_count+1'b1;
    if(&meter_count)begin peak_l<=ml>8064?63:ml[12:7];peak_r<=mr_peak>8064?63:mr_peak[12:7];ml<=al;mr_peak<=ar;end
    else begin if(al>ml)ml<=al;if(ar>mr_peak)mr_peak<=ar;end
   end
  end
 end
endmodule
