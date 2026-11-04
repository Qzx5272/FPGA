#include "Vv6_engine_probe.h"
#include "verilated.h"
#include <iostream>
#include <fstream>
#include <cstdlib>
double sc_time_stamp(){return 0;}
int main(int argc,char**argv){
 if(argc!=3)return 2;unsigned target=atoi(argv[2]),frames=0,maxvoices=0,maxcycles=0;int peak=0;
 Vv6_engine_probe d;std::ofstream f(argv[1],std::ios::binary);
 unsigned long long limit=(unsigned long long)target*1045+100000;
 for(unsigned long long c=0;c<limit&&frames<target;c++){
  d.clk=0;d.eval();d.clk=1;d.eval();
  if(d.valid){short a=d.left,b=d.right;f.write((char*)&a,2);f.write((char*)&b,2);frames++;
   maxvoices=std::max(maxvoices,unsigned(d.voices));maxcycles=std::max(maxcycles,unsigned(d.cycles));peak=std::max(peak,abs(int(a)));}
 }
 std::cout<<"frames="<<frames<<" peak="<<peak<<" maxvoices="<<maxvoices<<" maxcycles="<<maxcycles<<" deadline="<<d.deadline<<" clips="<<d.clips<<" drops="<<d.drops<<" underruns="<<d.underruns<<"\n";
 return !f.good()||frames!=target||!peak||d.deadline||d.clips||d.drops||d.underruns?1:0;
}
