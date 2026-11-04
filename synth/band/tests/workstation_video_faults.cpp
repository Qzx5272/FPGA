#include "Vworkstation_video_probe.h"
#include "verilated.h"
#include <iostream>
#include <algorithm>
#include <cstdint>
double sc_time_stamp(){return 0;}
int main(){
 VerilatedContext context;Vworkstation_video_probe d(&context);
 uint64_t nc=32256,na=65625,np=64000,now=0,cores=0;
 unsigned stalled_samples=0;bool saw_video=false,saw_fault=false,saw_clear=false;
 d.clk=d.audio_clk=d.pixel_clk=0;d.eval();
 // Exact50MHz/24.576MHz/25.2MHz clocks;140ms, no skipped core edges.
 while(cores<7000000){
  uint64_t next=std::min(std::min(nc,na),np);context.timeInc(next-now);now=next;
  bool rise=false;
  if(next==nc){d.clk=!d.clk;rise=d.clk;nc+=32256;if(rise)++cores;}
  // Stop video100..120ms; stop audio110..113ms while video remains stopped.
  if(next==na){if(cores<5500000||cores>=5650000)d.audio_clk=!d.audio_clk;na+=65625;}
  if(next==np){if(cores<5000000||cores>=6000000)d.pixel_clk=!d.pixel_clk;np+=64000;}
  d.eval();if(!rise)continue;
  if(cores<5000000)saw_video|=d.dv;
  if(cores>=5000000&&cores<5500000&&d.pcm_valid)++stalled_samples;
  if(cores>100000&&cores<5500000&&(d.drops||d.underruns||d.deadline||d.clips||d.clock_fault)){
   std::cerr<<"FAIL audio interrupted by video stall\n";return 1;
  }
  if(cores>=5555000&&cores<5650000){
   saw_fault|=d.clock_fault;
   if(d.dv||d.rgb||d.playing||d.voices){std::cerr<<"FAIL stale display/audio while both clocks stopped\n";return 2;}
   saw_clear=true;
  }
  if(cores>=6500000&&(d.clock_fault||d.playing||d.voices||d.dv)){
   std::cerr<<"FAIL old performance or frame resumed\n";return 3;
  }
 }
 bool ok=saw_video&&saw_fault&&saw_clear&&stalled_samples>=479&&stalled_samples<=481;
 std::cout<<"video_before_fault="<<saw_video<<" audio_samples_during_video_stall="<<stalled_samples
  <<" clock_fault_seen="<<saw_fault<<" stopped_display_cleared="<<saw_clear
  <<" final_playing="<<unsigned(d.playing)<<" final_voices="<<d.voices<<" final_video_valid="<<unsigned(d.dv)<<"\n";
 d.final();return ok?0:4;
}
