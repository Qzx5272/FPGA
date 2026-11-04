#include "Vpartial_pool.h"
#include "verilated.h"
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
double sc_time_stamp(){return 0;}
int main(int argc,char** argv){
 if(argc!=4&&argc!=5)return 2;
 bool diverse=argc==5&&std::string(argv[4])=="diverse";
 VerilatedContext context;Vpartial_pool d(&context);
 auto tick=[&](){d.clk=0;d.eval();context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);};
 unsigned capacity=std::stoul(argv[2]),frames=std::stoul(argv[3]);
 std::ofstream out(argv[1]);if(!out)return 3;
 d.rst=1;d.start=0;d.config_valid=0;tick();tick();d.rst=0;
 unsigned timeout=0;while(!d.initialized){tick();if(++timeout>2048)return 4;}
 for(unsigned i=0;i<capacity;i++){
  if(!d.config_ready)return 5;
  d.config_valid=1;d.config_address=i;d.config_phase=i*0x9e3779b9u;
  d.config_increment=(50+(capacity>16384?1:capacity>8192?3:5)*i)*32768u;
  d.config_envelope=diverse?10000+(i*31)%50000:50000;
  d.config_target=diverse?45000+(i*37)%15000:60000;
  d.config_slew=diverse?17+i%29:17;tick();
 }
 d.config_valid=0;tick();unsigned maximum_cycles=0;
 for(unsigned frame=0;frame<frames;frame++){
  d.start=1;tick();d.start=0;unsigned cycles=0;
  while(!d.valid_out){tick();if(++cycles>=1041)return 6;}
  if(d.active_count!=capacity||d.deadline_miss)return 7;
  if(d.last_cycles>maximum_cycles)maximum_cycles=d.last_cycles;
  int32_t sample=int32_t(d.sample_out<<8)>>8;out<<sample<<'\n';tick();
 }
 d.final();std::cout<<"PASS capacity="<<capacity<<" frames="<<frames<<" max_cycles="<<maximum_cycles<<"\n";
}
