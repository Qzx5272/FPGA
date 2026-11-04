// One 50 MHz domain, 64 BCLK/frame. Fractional enable averages exactly 48 kHz.
// Dedicated DAC and microphone pins are driven from coherent internal clocks.
module audio48_duplex #(parameter WARMUP=8192)(
 input clk,rst,halt,frame_valid,input signed[15:0]left,right,input mic_sd,
 output reg bck,ws,sd,output reg sample_tick,
 output reg signed[23:0] microphone,output reg mic_valid,
 output reg[31:0]dropped,underruns,output wire mic_ready);
 reg[25:0]phase;wire[26:0]next_phase={1'b0,phase}+27'd6144000;
 reg[5:0]bitpos;reg[31:0]frame;reg[31:0]fifo[0:3];
 reg[1:0]rd,wr;reg[2:0]count;reg started;
 wire falling=next_phase>=50000000&&bck;
 wire boundary=falling&&bitpos==0;
 wire present=count!=0&&(started||count>=2);
 wire pop=boundary&&present&&!halt;
 wire push=frame_valid&&!halt&&(count<4||pop);
 reg[23:0]rx_shift;reg[13:0]warmup;
 (* ASYNC_REG="TRUE" *)reg mic_meta,mic_sync;
 wire[5:0]rx_bit=bitpos-1'b1;
 assign mic_ready=warmup>=WARMUP;
 always @(posedge clk)begin
  if(rst)begin phase<=0;bck<=1;ws<=1;sd<=0;bitpos<=0;frame<=0;sample_tick<=0;
   rd<=0;wr<=0;count<=0;started<=0;dropped<=0;underruns<=0;
   mic_meta<=0;mic_sync<=0;rx_shift<=0;microphone<=0;mic_valid<=0;warmup<=0;
  end else begin
   mic_meta<=mic_sd;mic_sync<=mic_meta;sample_tick<=0;mic_valid<=0;
   if(next_phase>=50000000)begin
    phase<=next_phase-50000000;bck<=~bck;
    if(bck)begin
     bitpos<=bitpos+1'b1;ws<=bitpos>=31&&bitpos<63;
     if(bitpos==0)begin
      sample_tick<=1;frame<=present&&!halt?fifo[rd]:0;
      if(warmup<WARMUP)warmup<=warmup+1'b1;
     end
     if(halt)sd<=0;
     else if(bitpos==0)sd<=present?fifo[rd][31]:0;
     else if(bitpos<16)sd<=frame[31-bitpos];
     else if(bitpos>=32&&bitpos<48)sd<=frame[47-bitpos];
     else sd<=0;
    end else if(rx_bit<24)begin
     rx_shift<={rx_shift[22:0],mic_sync};
     if(rx_bit==23)begin microphone<=mic_ready?{rx_shift[22:0],mic_sync}:24'd0;mic_valid<=mic_ready;end
    end
   end else phase<=next_phase[25:0];
   if(halt)begin rd<=0;wr<=0;count<=0;started<=0;frame<=0;sd<=0;end
   else begin
    if(push)begin fifo[wr]<={left,right};wr<=wr+1'b1;end
    if(pop)begin rd<=rd+1'b1;started<=1;end
    case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
    if(frame_valid&&!push&&dropped!=32'hffffffff)dropped<=dropped+1'b1;
    if(boundary&&!present&&started&&underruns!=32'hffffffff)underruns<=underruns+1'b1;
   end
  end
 end
endmodule
