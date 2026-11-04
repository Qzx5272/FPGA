#include "Vworkstation_render.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc<3||argc>5)return 2;
 const bool load_fixture=argc>=4&&std::string(argv[3])=="--load";
 if(argc>=4&&!load_fixture)return 2;
 const uint64_t load_release=argc==5?std::stoull(argv[4]):5000;
 if(load_fixture&&load_release<=500)return 2;
 const uint64_t frames=std::stoull(argv[2]);
 std::ofstream out(argv[1],std::ios::binary);if(!out)return 3;
 VerilatedContext context;Vworkstation_render d(&context);
 // Integer rational schedule: unit=1/153.6GHz. No skipped core clocks.
 uint64_t next_core=1536,next_audio=3125,now=0,received=0;
 const uint64_t limit=(frames+48000)*3200000ULL;
 unsigned peak=0,maxvoices=0,maxcycles=0,checked_load=0;bool started=false,display=false;
 d.clk=0;d.audio_clk=0;d.eval();
 while(now<limit){
  uint64_t next=std::min(next_core,next_audio);context.timeInc(next-now);now=next;
  bool rise=false;
  if(next==next_core){d.clk=!d.clk;rise=d.clk;next_core+=1536;}
  if(next==next_audio){d.audio_clk=!d.audio_clk;next_audio+=3125;}
  d.eval();
  if(!rise)continue;
  if(d.playing)started=true;
  display|=d.display_available;
  if(started&&(d.drops||d.underruns||d.deadline||d.clips||d.fft_clips||d.rejected_bins||d.clock_fault)){
   std::cerr<<"FAIL drops="<<d.drops<<" underruns="<<d.underruns<<" deadline="<<d.deadline<<" clips="<<d.clips<<" fft_clips="<<d.fft_clips<<" rejected_bins="<<d.rejected_bins<<" clock_fault="<<unsigned(d.clock_fault)<<"\n";return 4;
  }
  if(started&&d.pcm_valid){
   if(load_fixture&&d.position>=500&&d.position<load_release){
    if(d.voices!=256){std::cerr<<"FAIL load position="<<d.position<<" voices="<<d.voices<<"\n";return 6;}
    ++checked_load;
   }
   int16_t l=d.left_out,r=d.right_out;out.write((char*)&l,2);out.write((char*)&r,2);++received;
   peak=std::max(peak,unsigned(std::max(std::abs(int(l)),std::abs(int(r)))));
   maxvoices=std::max(maxvoices,unsigned(d.voices));maxcycles=std::max(maxcycles,unsigned(d.cycles));
   if(received%48000==0)std::cerr<<"progress_frames="<<received<<" position="<<d.position<<"\n";
   if(received>=frames)break;
  }
 }
 out.flush();
 std::cout<<"received="<<received<<" peak="<<peak<<" max_voices="<<maxvoices<<" max_cycles="<<maxcycles<<" display_available="<<display<<" playing="<<unsigned(d.playing)<<" position="<<d.position<<" drops="<<d.drops<<" underruns="<<d.underruns<<" deadline="<<d.deadline<<" checked_load_frames="<<checked_load<<"\n";
 bool ok=received==frames&&peak>0&&display&&bool(out);
 if(!load_fixture&&frames>=4608001)ok=ok&&!d.playing&&d.position==4608000;
 if(load_fixture)ok=ok&&checked_load>=load_release-510&&!d.playing&&d.position==load_release+1000&&d.voices==0;
 d.final();return ok?0:5;
}
