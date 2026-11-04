#include "Vband_singer_core.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstdint>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc!=3)return 2;
 const unsigned frames=std::stoul(argv[2]);
 std::ofstream out(argv[1],std::ios::binary);if(!out)return 3;
 VerilatedContext context;Vband_singer_core d(&context);
 uint64_t clocks=0,issued=0,received=0,max_latency=0;unsigned peak=0,voices=0,cycles=0,sung=0;
 bool capture=false;bool invalid=false;
 auto tick=[&](){
  d.clk=0;d.eval();context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);++clocks;
  if(capture&&d.audio_valid){
   if(received>=issued){invalid=true;return;}
   // Frame n starts at floor(n*3125/3); capture completions across frame boundaries.
   uint64_t start=(received*3125)/3;
   max_latency=std::max(max_latency,clocks-start);
   int16_t l=d.left_out,r=d.right_out;
   out.write(reinterpret_cast<char*>(&l),2);out.write(reinterpret_cast<char*>(&r),2);
   peak=std::max(peak,unsigned(std::max(std::abs(int(l)),std::abs(int(r)))));++received;
  }
 };
 d.rst=1;d.panic=0;d.sample_tick=0;d.play=0;d.stop=0;
 d.manual_valid=0;d.command_valid=0;d.source_lost=0;d.upload_valid=0;d.control_valid=0;
 d.wet=24;d.master=64;d.tempo=120;d.transpose=0;d.singer_mix=127;d.microphone_sample=0;
 tick();tick();d.rst=0;for(unsigned i=0;i<9000;i++)tick();
 d.play=1;tick();d.play=0;clocks=0;capture=true;
 for(unsigned n=0;n<frames;n++){
  // Deterministic voiced excitation, NOT prerecorded voice or a natural-singing claim.
  double t=double(n)/48000.0;
  double envelope=0.55+0.45*std::sin(2*3.141592653589793*2*t);
  double mic=envelope*(std::sin(2*3.141592653589793*173*t)+0.4*std::sin(2*3.141592653589793*519*t)+0.2*std::sin(2*3.141592653589793*1211*t));
  d.microphone_sample=uint32_t(int32_t(mic*1000000))&0xffffff;
  ++issued;d.sample_tick=1;tick();d.sample_tick=0;
  for(unsigned c=1;c<(n%3==0?1041u:1042u);c++)tick();
  voices=std::max(voices,unsigned(d.active_voices));cycles=std::max(cycles,unsigned(d.render_cycles));
  sung+=d.singer_gate?1:0;
  if(invalid||d.deadline_miss||d.rejected||d.singer_dropped||!out){std::cerr<<"FAIL frame="<<n<<" deadline="<<d.deadline_miss<<" rejected="<<d.rejected<<" singer_dropped="<<d.singer_dropped<<"\n";return 4;}
  if(n%480000==0)std::cerr<<"progress_samples="<<n<<"\n";
 }
 for(unsigned i=0;i<3000;i++)tick();out.flush();
 std::cout<<"issued="<<issued<<" received="<<received<<" max_latency_clocks="<<max_latency<<" max_band_cycles="<<cycles<<" max_band_voices="<<voices<<" singer_held_samples="<<sung<<" peak="<<peak<<" clips="<<d.clips<<" singer_dropped="<<d.singer_dropped<<" deadline="<<d.deadline_miss<<" playing="<<unsigned(d.playing)<<" song_position="<<d.song_position<<"\n";
 if(invalid||received!=issued||!out||d.deadline_miss||d.singer_dropped||d.clips)return 5;
 if(frames>=4608000&&(d.playing||sung==0))return 6;
 d.panic=1;tick();if(d.left_out||d.right_out)return 7;
 d.final();return 0;
}
