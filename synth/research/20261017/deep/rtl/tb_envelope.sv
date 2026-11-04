module tb_envelope;
 reg clk=0;always #5 clk=~clk;
 reg rst=1,valid_in=0;
 reg [23:0] env=0,target=0;reg [26:0] rate=0;reg signed [24:0] remainder=0;
 wire valid_out;wire [23:0] next_env;wire signed [24:0] next_remainder;
 envelope_step dut(.*);
 integer fd,n,a,b,c,d,e,f,count=0,checked=0,head=0,tail=0,cycle=0;
 integer expect_e[0:40000],expect_r[0:40000];
 always @(negedge clk)begin
   if(!rst && valid_out)begin
     if(head>=tail || next_env!==expect_e[head][23:0] || next_remainder!==expect_r[head][24:0])begin
       $display("FAIL index=%0d env=%0d/%0d rem=%0d/%0d",head,next_env,expect_e[head],next_remainder,expect_r[head]);$fatal;
     end
     head=head+1;checked=checked+1;
   end
 end
 initial begin
   fd=$fopen("envelope_vectors.txt","r");if(!fd)$fatal;
   repeat(5)@(negedge clk);#1;rst=0;
   while(!$feof(fd))begin
     @(negedge clk);#1;cycle=cycle+1;
     if(cycle%13==0)valid_in=0;
     else begin
       n=$fscanf(fd,"%d %d %d %d %d %d\n",a,b,c,d,e,f);
       if(n==6)begin
         env=a;target=b;rate=c;remainder=d;valid_in=1;
         expect_e[tail]=e;expect_r[tail]=f;tail=tail+1;
       end else valid_in=0;
     end
   end
   @(negedge clk);#1;valid_in=0;
   repeat(10)@(negedge clk);#1;
   if(head!=tail)$fatal;
   $display("PASS envelope: %0d exact vectors, signed residual, boundary clamps and bubbles",checked);
   $finish;
 end
endmodule
