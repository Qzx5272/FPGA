// Iterative radix-2 DIT FFT, one complex RAM port, Q17 twiddles.
// Bit-reversed input storage and /2 per stage produce natural-order X[k]/N.
// No window is applied here. Input is exactly2**LOG_N signed16 complex samples.
// Output backpressure holds bin/data; this analysis module never clocks audio.
module fft_fixed #(parameter LOG_N=11,parameter TWIDDLE_FILE="fft_twiddle_2048.mem")(
 input clk,rst,start,output wire start_ready,
 input input_valid,output wire input_ready,input signed[15:0]input_real,input_imag,
 output reg output_valid,input output_ready,output reg[LOG_N-1:0]output_bin,
 output reg signed[15:0]output_real,output_imag,
 output reg done,output reg[31:0]rejected_starts,clip_count
);
 localparam N=1<<LOG_N;
 localparam IDLE=0,LOAD=1,READ_A=2,LATCH_A=3,READ_B=4,LATCH_B=5,MULT=6,SCALE=7,WRITE_A=8,WRITE_B=9,NEXT=10,OUT_READ=11,OUT_LATCH=12,OUT_HOLD=13;
 reg[3:0]state;
 reg[31:0]memory[0:N-1];reg[35:0]twiddle[0:N/2-1];
 initial $readmemh(TWIDDLE_FILE,twiddle);
 reg[LOG_N-1:0]load_index,base,offset,half_size,address_a,address_b;
 reg[3:0]stage;reg[31:0]read_word;reg[35:0]twiddle_word;
 reg signed[15:0]ar,ai,br,bi;
 reg signed[17:0]wr,wi;
 reg signed[33:0]rr,ii,ri,ir;
 wire signed[34:0]product_real=$signed({rr[33],rr})-$signed({ii[33],ii});
 wire signed[34:0]product_imag=$signed({ri[33],ri})+$signed({ir[33],ir});
 wire signed[17:0]tr=product_real>>>17,ti=product_imag>>>17;
 wire signed[18:0]sum_r=$signed(ar)+$signed(tr),sum_i=$signed(ai)+$signed(ti);
 wire signed[18:0]diff_r=$signed(ar)-$signed(tr),diff_i=$signed(ai)-$signed(ti);
 reg signed[15:0]result_ar,result_ai,result_br,result_bi;
 function[LOG_N-1:0]reverse_bits(input[LOG_N-1:0]v);
 integer j;begin for(j=0;j<LOG_N;j=j+1)reverse_bits[j]=v[LOG_N-1-j];end endfunction
 // Saturation protects arbitrary complex full-scale inputs, whose vector norm
 // may exceed1; callers should leave complex headroom for quantitative spectra.
 function[15:0]scaled(input signed[18:0]v);
 reg signed[18:0]q;begin q=v>>>1;
 if(q>32767)scaled=16'h7fff;else if(q< -32768)scaled=16'h8000;else scaled=q[15:0];end endfunction
 assign start_ready=!rst&&state==IDLE;
 assign input_ready=!rst&&state==LOAD;
 wire memory_write=(state==LOAD&&input_valid)||state==WRITE_A||state==WRITE_B;
 wire[LOG_N-1:0] memory_write_address=state==LOAD?reverse_bits(load_index):state==WRITE_A?address_a:address_b;
 wire[31:0] memory_write_data=state==LOAD?{input_real,input_imag}:state==WRITE_A?{result_ar,result_ai}:{result_br,result_bi};
 wire memory_read=state==READ_A||state==READ_B||state==OUT_READ;
 wire[LOG_N-1:0] memory_read_address=state==READ_A?base+offset:state==READ_B?address_b:output_bin;
 always @(posedge clk)begin
  if(!rst)begin
   if(memory_write)memory[memory_write_address]<=memory_write_data;
   if(memory_read)read_word<=memory[memory_read_address];
   if(state==READ_A)twiddle_word<=twiddle[offset<<(LOG_N-1-stage)];
  end
 end
 always @(posedge clk)begin
  if(rst)begin
   state<=IDLE;output_valid<=0;output_bin<=0;output_real<=0;output_imag<=0;done<=0;rejected_starts<=0;clip_count<=0;
   load_index<=0;base<=0;offset<=0;half_size<=1;address_a<=0;address_b<=0;stage<=0;
   ar<=0;ai<=0;br<=0;bi<=0;wr<=0;wi<=0;rr<=0;ii<=0;ri<=0;ir<=0;
   result_ar<=0;result_ai<=0;result_br<=0;result_bi<=0;
  end else begin
   done<=0;
   if(start&&!start_ready&&rejected_starts!=32'hffffffff)rejected_starts<=rejected_starts+1'b1;
   case(state)
    IDLE:if(start)begin load_index<=0;clip_count<=0;state<=LOAD;end
    LOAD:if(input_valid)begin
     if(load_index==N-1)begin base<=0;offset<=0;half_size<=1;stage<=0;state<=READ_A;end
     else load_index<=load_index+1'b1;
    end
    READ_A:begin address_a<=base+offset;address_b<=base+offset+half_size;state<=LATCH_A;end
    LATCH_A:begin ar<=read_word[31:16];ai<=read_word[15:0];wr<=twiddle_word[35:18];wi<=twiddle_word[17:0];state<=READ_B;end
    READ_B:state<=LATCH_B;
    LATCH_B:begin br<=read_word[31:16];bi<=read_word[15:0];state<=MULT;end
    MULT:begin rr<=br*wr;ii<=bi*wi;ri<=br*wi;ir<=bi*wr;state<=SCALE;end
    SCALE:begin
     result_ar<=scaled(sum_r);result_ai<=scaled(sum_i);result_br<=scaled(diff_r);result_bi<=scaled(diff_i);state<=WRITE_A;
     if((sum_r>65535||sum_r< -65536||sum_i>65535||sum_i< -65536||diff_r>65535||diff_r< -65536||diff_i>65535||diff_i< -65536)&&clip_count!=32'hffffffff)clip_count<=clip_count+1'b1;
    end
    WRITE_A:state<=WRITE_B;
    WRITE_B:state<=NEXT;
    NEXT:begin
     if(offset==half_size-1)begin
      offset<=0;
      if({1'b0,base}+({1'b0,half_size}<<1)>=N)begin
       base<=0;
       if(stage==LOG_N-1)begin output_bin<=0;state<=OUT_READ;end
       else begin half_size<=half_size<<1;stage<=stage+1'b1;state<=READ_A;end
      end else begin base<=base+(half_size<<1);state<=READ_A;end
     end else begin offset<=offset+1'b1;state<=READ_A;end
    end
    OUT_READ:state<=OUT_LATCH;
    OUT_LATCH:begin output_real<=read_word[31:16];output_imag<=read_word[15:0];output_valid<=1;state<=OUT_HOLD;end
    OUT_HOLD:if(output_ready)begin
     output_valid<=0;
     if(output_bin==N-1)begin done<=1;state<=IDLE;end
     else begin output_bin<=output_bin+1'b1;state<=OUT_READ;end
    end
    default:begin output_valid<=0;state<=IDLE;end
   endcase
  end
 end
endmodule
