// 8-frame Gray-pointer CDC FIFO. Payload is stable before synchronized pointer publication.
// Both domains must share asynchronous reset assertion; each releases it synchronously.
module audio_cdc_fifo #(parameter ADDRESS_BITS=3)(
 input wire write_clk,write_rst,write_valid,input wire [47:0] write_data,
 output wire write_ready,input wire read_clk,read_rst,read_pop,
 output wire read_valid,output wire [47:0] read_data
);
 localparam WIDTH=ADDRESS_BITS+1;
 reg [47:0] memory[0:(1<<ADDRESS_BITS)-1];
 reg [WIDTH-1:0] wbin,wgray,rbin,rgray;
 (* async_reg="true" *) reg [WIDTH-1:0] rgray_w1,rgray_w2,wgray_r1,wgray_r2;
 reg full,empty;
 wire [WIDTH-1:0] wn=wbin+(write_valid&&!full),rn=rbin+(read_pop&&!empty);
 wire [WIDTH-1:0] wg=(wn>>1)^wn,rg=(rn>>1)^rn;
 assign write_ready=!full&&!write_rst;assign read_valid=!empty&&!read_rst;
 assign read_data=memory[rbin[ADDRESS_BITS-1:0]];
 always @(posedge write_clk or posedge write_rst)begin
  if(write_rst)begin wbin<=0;wgray<=0;full<=0;rgray_w1<=0;rgray_w2<=0;end
  else begin
   rgray_w1<=rgray;rgray_w2<=rgray_w1;
   wbin<=wn;wgray<=wg;
   full<=wg=={~rgray_w2[WIDTH-1:WIDTH-2],rgray_w2[WIDTH-3:0]};
  end
 end
 always @(posedge write_clk)if(write_valid&&write_ready)memory[wbin[ADDRESS_BITS-1:0]]<=write_data;
 always @(posedge read_clk or posedge read_rst)begin
  if(read_rst)begin rbin<=0;rgray<=0;empty<=1;wgray_r1<=0;wgray_r2<=0;end
  else begin
   wgray_r1<=wgray;wgray_r2<=wgray_r1;
   rbin<=rn;rgray<=rg;empty<=rg==wgray_r2;
  end
 end
endmodule
