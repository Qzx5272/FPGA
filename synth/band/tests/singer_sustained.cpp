#include "Vband_singer_core.h"
#include "verilated.h"
#include <iostream>
#include <fstream>
#include <algorithm>
#include <cstdint>
#include <stdexcept>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 const uint64_t loaded=std::stoull(argv[2]);
 std::ofstream out(argv[1],std::ios::binary);if(!out)return 3;
 VerilatedContext context;Vband_singer_core d(&context);
 uint64_t issued=0,received=0,clocks=0,max_latency=0,nonzero=0;
 unsigned peak=0,max_cycles=0,min_voices=65535;bool capture=false;
 auto require=[](bool ok,const char*msg){if(!ok)throw std::runtime_error(msg);};
 auto tick=[&](){
  d.clk=0;d.eval();context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);++clocks;
  if(capture&&d.audio_valid){
   require(received<issued,"unsolicited/duplicate PCM");
   max_latency=std::max(max_latency,clocks-(received*3125)/3);
   int16_t l=d.left_out,r=d.right_out;out.write((char*)&l,2);out.write((char*)&r,2);
   peak=std::max(peak,unsigned(std::max(std::abs(int(l)),std::abs(int(r)))));
   nonzero+=(l!=0||r!=0);++received;
  }
 };
 try{
  d.rst=1;d.panic=0;d.sample_tick=0;d.play=0;d.stop=0;d.manual_valid=0;d.command_valid=0;d.source_lost=0;d.upload_valid=0;d.control_valid=0;
  d.master=4;d.wet=24;d.tempo=120;d.transpose=0;d.singer_mix=100;d.microphone_sample=0;
  d.manual_source=1;d.manual_kind=0;d.manual_velocity=100;d.command_source=1;d.command=0;d.control_source=1;d.control_parameter=7;d.control_value=0;d.control_epoch=0;
  tick();tick();d.rst=0;for(int i=0;i<9000;i++)tick();
  auto take=[&](unsigned part){
   d.command_part=part;d.status_part=part;d.manual_part=part;d.command_valid=1;d.eval();
   unsigned timeout=0;while(!d.command_ready){require(++timeout<10000,"take timeout");tick();}tick();d.command_valid=0;
   for(int i=0;i<100;i++)tick();require(d.status_owner==1,"ownership not acquired");d.manual_epoch=d.status_epoch;
  };
  auto note=[&](unsigned contact,unsigned serial,unsigned pitch){
   d.manual_contact=contact;d.manual_serial=serial;d.manual_note=pitch;d.manual_valid=1;d.eval();
   unsigned timeout=0;while(!d.manual_ready){require(++timeout<10000,"note timeout");tick();}tick();d.manual_valid=0;
   for(int i=0;i<4;i++)tick();
  };
  take(15);note(0,1,60);for(int i=0;i<100;i++)tick();
  for(unsigned bank=0;bank<8;bank++){
   unsigned part=bank==7?7:bank+8;take(part);
   d.control_part=part;d.control_valid=1;tick();d.control_valid=0;for(int i=0;i<8;i++)tick();
   for(unsigned i=0;i<32;i++)note(i,1000+bank*32+i,40+i);
   for(int i=0;i<100;i++)tick();
  }
  // active_voices is refreshed by the audio frame; before the first tick it
  // still reports reset's zero. Check256 after every actual rendered frame.
  require(d.singer_gate,"initial singer note missing");
  clocks=0;capture=true;uint32_t noise=0x12345678;
  auto frame=[&](){
   const auto n=issued++;noise=(noise<<1)|(((noise>>31)^(noise>>21)^(noise>>1)^noise)&1);
   d.microphone_sample=noise&0xffffff;d.sample_tick=1;tick();d.sample_tick=0;
   for(unsigned i=1;i<(n%3==0?1041u:1042u);i++)tick();
   max_cycles=std::max(max_cycles,unsigned(d.render_cycles));
   require(!d.deadline_miss&&!d.rejected&&!d.singer_dropped&&!d.clips,"audio error counter");
  };
  for(uint64_t n=0;n<loaded;n++){
   frame();min_voices=std::min(min_voices,unsigned(d.active_voices));
   require(d.active_voices==256&&d.singer_gate,"sustained load lost");
   if(n%480000==0)std::cerr<<"progress_samples="<<n<<"\n";
  }
  // No clocks are skipped. Release at a sample boundary while audio continues.
  d.source_lost=1;d.lost_source=1;d.eval();require(d.lost_ready,"source release not ready at boundary");
  // Keep release asserted for exactly one clock, then finish this regular frame.
  ++issued;d.sample_tick=1;tick();d.sample_tick=0;d.source_lost=0;
  for(unsigned c=1;c<((issued-1)%3==0?1041u:1042u);c++)tick();
  for(int i=0;i<31;i++)frame();
  for(int i=0;i<3000;i++)tick();out.flush();
  require(received==issued&&out.good(),"PCM count/write mismatch");
  require(!d.active_voices&&!d.singer_gate,"source release incomplete");
  require(!d.deadline_miss&&!d.rejected&&!d.singer_dropped&&!d.clips,"final counters");
  d.panic=1;tick();require(!d.left_out&&!d.right_out,"panic failed");
  std::cout<<"PASS loaded_frames="<<loaded<<" issued="<<issued<<" received="<<received<<" min_sustained_band_voices="<<min_voices<<" singer_held=1 max_band_cycles="<<max_cycles<<" max_latency_clocks="<<max_latency<<" peak="<<peak<<" nonzero_frames="<<nonzero<<" clips=0 drops=0 deadline=0 source_release=passed panic=passed\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<" issued="<<issued<<" received="<<received<<" voices="<<d.active_voices<<" clips="<<d.clips<<" deadline="<<d.deadline_miss<<" dropped="<<d.singer_dropped<<"\n";return 1;}
 d.final();return 0;
}
