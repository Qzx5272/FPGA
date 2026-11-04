#include "Vpartial_pool.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <algorithm>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc!=4)return 2;
 const unsigned capacity=std::stoul(argv[2]),frames=std::stoul(argv[3]);
 const unsigned frequency_step=capacity<=8192?5:capacity<=16384?3:1;
 if(!capacity || 50+frequency_step*(capacity-1)>=65536)return 12;
 std::ofstream out(argv[1]);if(!out)return 3;
 VerilatedContext context;Vpartial_pool d(&context);
 uint64_t clocks=0;
 auto tick=[&](){d.clk=0;d.eval();context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);++clocks;};
 d.rst=1;d.start=0;d.config_valid=0;tick();tick();d.rst=0;
 unsigned timeout=0;while(!d.initialized){tick();if(++timeout>2048)return 4;}
 for(unsigned i=0;i<capacity;i++){
  if(!d.config_ready)return 5;
  d.config_valid=1;d.config_address=i;d.config_phase=i*0x9e3779b9u;
  d.config_increment=(50+frequency_step*i)*32768u;
  d.config_envelope=10000+(i*31)%50000;
  d.config_target=45000+(i*37)%15000;d.config_slew=17+i%29;tick();
 }
 d.config_valid=0;tick();const uint64_t origin=clocks;
 unsigned received=0,max_latency=0,max_cycles=0;
 for(unsigned frame=0;frame<frames;frame++){
  if(clocks-origin!=uint64_t(frame)*3125/3)return 6;
  const unsigned period=frame%3==0?1041:1042;
  unsigned completions=0;
  for(unsigned c=0;c<period;c++){
   d.start=c==0;tick();
   if(d.deadline_miss)return 7;
   if(d.valid_out){
    if(++completions!=1||d.active_count!=capacity)return 8;
    max_latency=std::max(max_latency,c+1);max_cycles=std::max(max_cycles,unsigned(d.last_cycles));
    out<<(int32_t(d.sample_out<<8)>>8)<<'\n';++received;
   }
  }
  if(completions!=1)return 9;
 }
 out.flush();if(!out||received!=frames)return 10;
 std::cout<<"PASS capacity="<<capacity<<" frames="<<frames<<" received="<<received
          <<" audio_clocks="<<clocks-origin<<" max_latency="<<max_latency<<" max_cycles="<<max_cycles
          <<" fixed_core_hz=50000000 sample_rate=48000\n";
 d.final();return 0;
}
