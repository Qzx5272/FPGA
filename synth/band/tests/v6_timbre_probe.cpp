#include "Vv6_timbre_probe.h"
#include "verilated.h"
#include <fstream>
#include <iostream>
#include <string>
#include <cstdlib>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc!=8)return 2;
 Vv6_timbre_probe d;d.part=atoi(argv[2]);d.note=atoi(argv[3]);d.attack=atoi(argv[4]);
 d.decay=atoi(argv[5]);d.sustain=atoi(argv[6]);d.release_rate=atoi(argv[7]);d.gate=1;d.panic=0;d.tick=0;d.rst=1;
 auto clock=[&](){d.clk=0;d.eval();d.clk=1;d.eval();};
 for(int i=0;i<8;i++)clock();d.rst=0;
 std::ofstream f(argv[1],std::ios::binary);int peak=0,count=0;long long power=0;unsigned maxcycles=0;
 for(int frame=0;frame<18000;frame++){
  if(frame==12000)d.gate=0;
  int generated=0;
  for(int c=0;c<1042;c++){d.tick=c==0;clock();if(d.valid){
   short a=d.left,b=d.right;f.write((char*)&a,2);f.write((char*)&b,2);
   peak=std::max(peak,abs(int(a)));power+=(long long)a*a;generated++;count++;maxcycles=std::max(maxcycles,unsigned(d.cycles));
  }}
  if(generated!=1){std::cerr<<"frame_count="<<generated<<" at "<<frame;return 3;}
 }
 d.panic=1;clock();d.panic=0;d.tick=0;for(int i=0;i<64;i++)clock();
 std::cout<<"frames="<<count<<" peak="<<peak<<" power="<<power<<" deadline="<<d.deadline<<" clips="<<d.clips<<" cycles="<<maxcycles<<"\n";
 return !f.good()||!peak||d.deadline||d.clips?1:0;
}
