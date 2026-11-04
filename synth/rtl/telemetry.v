module telemetry(input clk,rst,packet_valid,online,
    input [7:0] sequence,keys, input [3:0] voices, input [15:0] peak,
    output tx);
    reg [7:0] message[0:9];
    reg [3:0] index;
    reg sending, launch, waiting;
    wire busy;
    reg [7:0] data;
    uart_tx transmitter(clk,rst,data,launch,tx,busy);
    always @(posedge clk) begin
        if(rst) begin index<=0; sending<=0; launch<=0; waiting<=0; data<=0; end
        else begin
            launch<=0;
            if(packet_valid && !sending) begin
                message[0]<=8'h5a; message[1]<=8'ha5; message[2]<=sequence;
                message[3]<=keys; message[4]<={4'b0,voices}; message[5]<=peak[7:0]; message[6]<=peak[15:8];
                message[7]<={7'b0,online}; message[8]<=2;
                message[9]<=sequence^keys^{4'b0,voices}^peak[7:0]^peak[15:8]^{7'b0,online}^8'd2;
                index<=0; sending<=1; waiting<=0;
            end else if(sending) begin
                if(!waiting && !busy && !launch) begin data<=message[index]; launch<=1; waiting<=1; end
                else if(waiting && busy) begin
                    waiting<=0;
                    if(index==9) sending<=0; else index<=index+1;
                end
            end
        end
    end
endmodule
