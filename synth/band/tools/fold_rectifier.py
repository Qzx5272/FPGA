"""Fold the 16 simultaneous envelope rectifiers into a pipelined band scan."""
def fold_rectifier(path):
    text=path.read_text()
    code="""  logic [4:0] rect_index;
  logic [3:0] rect_tag,write_tag;
  logic rect_read,rect_write;
  logic [31:0] rect_input[0:2],rect_result[0:2];
  // abs(INT_MIN) saturates. Split the unsigned increment into halves so its
  // carry never crosses a band mux and a full 32-bit adder in one clock.
  for(genvar lane=0;lane<3;lane++)begin:rect_lane
    wire [31:0] value=rect_input[lane];
    wire [31:0] ones=value^{32{value[31]}};
    reg [16:0] low_sum;reg [15:0] high;reg saturate;
    always @(posedge clk_in)begin
      low_sum<={1'b0,ones[15:0]}+value[31];
      high<=ones[31:16];saturate<=value==32'h80000000;
    end
    assign rect_result[lane]=saturate?32'h7fffffff:{16'(high+low_sum[16]),low_sum[15:0]};
  end
  always @(posedge clk_in)begin
    if(rst_in||state!=RECTIFY)begin rect_index<=0;rect_read<=0;rect_write<=0;end
    else begin
      rect_read<=rect_index<16;rect_write<=rect_read;
      if(rect_index<16)begin
        rect_tag<=rect_index[3:0];rect_index<=rect_index+1'b1;
        rect_input[0]<=x_n[rect_index[3:0]];
        rect_input[1]<=x_n1[rect_index[3:0]];
        rect_input[2]<=x_n2[rect_index[3:0]];
      end
      write_tag<=rect_tag;
    end
  end
"""
    pos=text.index('  // Experimental: four arithmetic')
    text=text[:pos]+code+text[pos:]
    start=text.index('        RECTIFY: begin')
    end=text.index('        ENVELOPE: begin',start)
    text=text[:start]+"""        RECTIFY: begin
          filters_valid_in<=0;
          if(rect_write)begin
            x_n[write_tag]<=rect_result[0];
            x_n1[write_tag]<=rect_result[1];
            x_n2[write_tag]<=rect_result[2];
            if(write_tag==15)begin filters_valid_in<=1;state<=ENVELOPE;end
          end
        end
"""+text[end:]
    path.write_text(text)

