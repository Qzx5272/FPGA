#include "Vband_core.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <cstdint>
#include <algorithm>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc<3||argc>4)return 2;
 bool fast=argc==4&&std::string(argv[3])=="fast";
 bool stress=argc==4&&std::string(argv[3])=="stress";
 bool matrix=argc==4&&std::string(argv[3])=="matrix";
 bool audition=argc==4&&(std::string(argv[3])=="audition"||std::string(argv[3])=="audition_fast"||matrix);
 if(argc==4&&(std::string(argv[3])=="audition_fast"||matrix))fast=true;
 if(stress)fast=true;
 unsigned frames=std::stoul(argv[2]);std::ofstream out(argv[1],std::ios::binary);if(!out)return 3;
 VerilatedContext context;Vband_core d(&context);
 auto tick=[&](){
  d.clk=0;d.eval();bool cm=d.command_valid&&d.command_ready,ma=d.manual_valid&&d.manual_ready,lo=d.source_lost&&d.lost_ready;
  context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);
  if(cm)d.command_valid=0;if(ma)d.manual_valid=0;if(lo)d.source_lost=0;
 };
 d.rst=1;d.panic=0;d.sample_tick=0;d.play=0;d.stop=0;d.manual_valid=0;d.command_valid=0;d.source_lost=0;
 d.upload_valid=0;d.upload_command=0;d.upload_index=0;d.upload_value=0;d.upload_aux=0;
 d.control_valid=0;d.control_part=0;d.control_source=1;d.control_epoch=0;d.control_parameter=0;d.control_value=0;
 d.manual_kind=0;d.manual_source=1;d.manual_contact=60;d.manual_part=6;d.manual_epoch=1;d.manual_serial=10000;d.manual_note=76;d.manual_velocity=110;
 d.command=0;d.command_part=6;d.command_source=1;d.wet=32;d.master=96;d.tempo=120;d.transpose=0;d.status_part=6;d.lost_source=1;
 tick();tick();d.rst=0;for(unsigned i=0;i<8300;i++)tick();
 if(stress){
  d.master=4;d.wet=0;
  for(unsigned p=0;p<8;p++){
   unsigned part=p==7?7:p+8;
   d.command_part=part;d.status_part=part;d.command_valid=1;
   for(unsigned guard=0;d.command_valid&&guard<1000;guard++)tick();
   for(unsigned i=0;i<100;i++)tick();
   if(d.status_owner!=1)return 20;
   d.control_part=part;d.control_parameter=1;d.control_value=8192+256*p;d.control_valid=1;tick();d.control_valid=0;
   for(unsigned v=0;v<32;v++){
    d.manual_part=part;d.manual_contact=v;d.manual_note=40+v;d.manual_velocity=70+(p*7+v)%50;
    d.manual_epoch=d.status_epoch;d.manual_serial=10000+p*32+v;d.manual_valid=1;
    for(unsigned guard=0;d.manual_valid&&guard<1000;guard++)tick();
    if(d.manual_valid)return 21;
   }
  }
  for(unsigned i=0;i<100;i++)tick();
 }else if(audition){
  for(unsigned p: {4u,5u,7u}){d.command_part=p;d.status_part=p;d.command_valid=1;for(unsigned i=0;i<200;i++)tick();if(d.status_owner!=1)return 23;}
  d.wet=0;d.master=96;
 }else{d.play=1;tick();d.play=0;}
 unsigned maximum_cycles=0,maximum_voices=0,missing=0,take_checks=0,return_checks=0,peak=0,minimum_sustained_voices=65535;
 unsigned release_frame=frames>96000?frames-48000:frames/2;
 for(unsigned n=0;n<frames;n++){
  if(stress&&n==release_frame){d.manual_kind=2;d.manual_source=1;d.manual_valid=1;}
  if(stress&&n%4800==0&&n<release_frame){d.control_part=7;d.control_parameter=0;d.control_value=64+(n/4800)%64;d.control_valid=1;tick();d.control_valid=0;}
  if(audition){
   unsigned section=n/48000,offset=n%48000;
   if(offset==0){
    d.control_part=matrix?(section/9==0?4:5):section==0?4:section==1||section>=7?5:7;
    d.control_parameter=matrix?1:section>=7?1:2;d.control_value=matrix?8192:section>=7?(section==7?8192:section==8?16383:0):(section>=2?section-2:0);d.control_valid=1;tick();d.control_valid=0;
    d.manual_part=d.control_part;d.manual_epoch=2;d.manual_serial=10000+section;d.manual_note=matrix?45+24*((section%9)/3):d.manual_part==7?57:69;d.manual_velocity=matrix?(section%3==0?32:section%3==1?80:127):110;d.manual_kind=0;d.manual_valid=1;
   }
   if(offset==38400){d.manual_kind=1;d.manual_valid=1;}
  }
  if(!stress&&!audition){
   if(n==34*48000){d.command=0;d.command_source=1;d.command_valid=1;}
   if(n==34*48000+100){if(d.status_owner!=1)return 10;take_checks++;d.manual_epoch=d.status_epoch;d.manual_kind=0;d.manual_valid=1;}
   if(n==35*48000){d.manual_kind=1;d.manual_valid=1;}
   if(n==36*48000){d.command=0;d.command_source=2;d.command_valid=1;}
   if(n==36*48000+100&&d.status_owner!=1)return 11;
   if(n==37*48000){d.command=1;d.command_source=1;d.command_valid=1;}
   if(n==38*48000+100){if(d.status_owner!=0)return 12;return_checks++;}
  }
  d.sample_tick=1;tick();d.sample_tick=0;unsigned valid_count=d.audio_valid?1:0;
  // True fabric/sample ratio alternates 1041,1042,1042 clocks at 50 MHz / 48 kHz.
  unsigned clocks=n%3==0?1041:1042;
  for(unsigned c=1;c<clocks;c++){
   tick();if(d.audio_valid)valid_count++;
   if(fast&&d.simulation_idle){context.timeInc(2*(clocks-c-1));break;}
  }
  if(valid_count!=1)missing++;
  if(d.deadline_miss||d.rejected){std::cerr<<"FAIL frame="<<n<<" deadline="<<d.deadline_miss<<" rejected="<<d.rejected<<"\n";return 13;}
  maximum_cycles=std::max(maximum_cycles,unsigned(d.render_cycles));maximum_voices=std::max(maximum_voices,unsigned(d.active_voices));
  if(stress&&n>4800&&n<release_frame){minimum_sustained_voices=std::min(minimum_sustained_voices,unsigned(d.active_voices));if(d.active_voices!=256)return 24;}
  int16_t l=d.left_out,r=d.right_out;peak=std::max(peak,unsigned(std::max(std::abs(int(l)),std::abs(int(r)))));
  out.write(reinterpret_cast<char*>(&l),2);out.write(reinterpret_cast<char*>(&r),2);
  if(!out){std::cerr<<"FAIL output write at frame "<<n<<"\n";return 30;}
 }
 out.flush();if(!out){std::cerr<<"FAIL output flush\n";return 31;}
 std::cout<<"frames="<<frames<<" max_cycles="<<maximum_cycles<<" max_voices="<<maximum_voices<<" missing="<<missing<<" clips="<<d.clips<<" peak="<<peak<<" takeover_checks="<<take_checks<<" return_checks="<<return_checks<<" denied="<<d.denied<<" lead_space="<<d.lead_space_events<<" kick_follow="<<d.kick_follow_events<<" min_sustained_voices="<<(stress?minimum_sustained_voices:0)<<"\n";
 if(missing||maximum_cycles>=1041)return 14;
 if(stress&&(maximum_voices!=256||d.active_voices!=0||d.clips))return 22;
 d.panic=1;tick();if(d.left_out||d.right_out)return 15;
 d.final();std::cout<<"PASS integrated band simulation\n";
}
