#include <cassert>
#include <string>
#include <array>
#include <cstdio>
#include <vector>
#include "src/pad_fpga.h"
#include <Preferences.h>
std::vector<unsigned char> Preferences::memory;
std::vector<std::array<uint8_t,34>> notes;
bool sendNote(const uint8_t*p){std::array<uint8_t,34>a;memcpy(a.data(),p,34);notes.push_back(a);return true;}
PadFpga padFpga(sendNote);
uint32_t now=100;
uint32_t millis(){return now;}
struct Console{void println(const char*){}} Serial;
struct Device{struct Address{std::string toString(){return "00:11:22:33:44:55";}};Address getPeerAddress(){return {};}bool isConnected(){return true;}} device;
auto client=&device;
bool configNotify=true;int phonePhase=0,command=-1;
std::vector<uint8_t> data;
bool sendConfig(uint8_t cmd,const uint8_t*p,size_t n){assert(command==-1);command=cmd;data.clear();if(n)data.assign(p,p+n);return true;}
#include "src/pad_lesson.h"
std::array<uint8_t,11724> records{};
const int base=3*2931+16*26;
void pump(){
 for(int guard=160;--guard;){
  lesson.tick();
  if(command<0)return;
  auto d=data;int c=command;command=-1;
  if(c==0x11){const char model[]="SMC-PAD Pocket_004";lesson.receive(c,(const uint8_t*)model,sizeof(model));continue;}
  unsigned addr=d[1]+d[2]*256,len=d[5]+d[6]*256;assert((addr>=base&&addr+len<=base+16*26)||(addr>=11705&&addr+len<=11721));
  if(c==0x23){d.insert(d.end(),records.begin()+addr,records.begin()+addr+len);lesson.receive(c,d.data(),d.size());}
  else{assert(c==0x22&&((len==3&&(addr-base)%26==5)||(len==4&&(addr==11713||addr==11717))));memcpy(records.data()+addr,d.data()+8,len);uint8_t ok=0;lesson.receive(0,&ok,1);}
 }
 assert(false);
}
int color(int k){auto p=records.data()+base+26*k+5;return p[0]*65536+p[1]*256+p[2];}
int main(){
 for(int k=0;k<16;++k){records[base+k*26+1]=9;records[base+k*26+2]=20+k;}
 padFpga.online=padFpga.configKnown=padFpga.enabled=true;padFpga.owner=2;
 const uint8_t controls[]={5,4,7,6,1,8,3,2};memcpy(records.data()+11713,controls,8);lesson.setup();pump();for(int i=11713;i<11721;i++)assert(!records[i]);for(int k=0;k<16;++k)assert(color(k)==0x2058e8);auto normal=records;
 for(int octave=-3;octave<=4;octave++){
  padFpga.octave=octave;pump();
  for(int k=1;k<16;k++)assert(color(k)==color(0));
  if(octave!=0)assert(records!=normal);
 }
 padFpga.octave=0;pump();assert(records==normal);
 assert(!lesson.midi(0x99,35,80));lesson.midi(0x89,35,0);pump();assert(color(15)==0xffffff);
 now+=200;pump();assert(records==normal);
 padFpga.lessonRequested=true;pump();
 int score[]={0,0,4,4,5,5,4,3,3,2,2,1,1,0,4,4,3,3,2,2,1,4,4,3,3,2,2,1,0,0,4,4,5,5,4,3,3,2,2,1,1,0};
 for(int k:score){
  assert(color(k)==0xffcf00);
  auto before=notes.size();int wrong=(k+1)%6;
  lesson.midi(0x99,20+wrong,83);lesson.midi(0x89,20+wrong,0);pump();assert(notes.size()==before&&color(wrong)==0xffffff);
  assert(lesson.midi(0x99,20+k,40));assert(notes.back()[3]==0&&notes.back()[8]==96);
  lesson.midi(0x89,20+k,0);pump();assert(color(k)==0xffffff);
  now+=1000;pump();assert(notes.back()[3]==1);
 }
 padFpga.lessonRequested=false;pump();assert(records==normal);
 padFpga.scoreGuide=true;padFpga.lessonRequested=true;padFpga.cue=31;padFpga.cueTag=0x1234;
 pump();assert(color(15)==0xffcf00);auto n=notes.size();
 lesson.midi(0x99,20,88);lesson.midi(0x89,20,0);assert(notes.size()==n);
 lesson.midi(0x99,35,88);assert(notes.back()[3]==22&&notes.back()[6]==15&&starcluster::u32(notes.back().data()+14)==0x1234);
 lesson.midi(0x89,35,0);padFpga.lessonRequested=false;now+=300;pump();now+=300;pump();
 padFpga.scorePlaying=true;padFpga.scoreIndex=2;padFpga.part=4;padFpga.owner=2;
 const auto& chord=chordPads[2][4][0];assert(chord[0]>1);auto old=notes.size();
 assert(lesson.midi(0x99,20,90));assert(notes.size()==old+chord[0]);
 for(unsigned i=0;i<chord[0];++i)assert(notes[old+i][7]==chord[1+i]);
 assert(lesson.midi(0x89,20,0));assert(notes.size()==old+2*chord[0]);
 padFpga.scorePlaying=false;lesson.disconnected();pump();assert(records==normal);
 puts("PASS 16 pads, pitch groups, quick tap, wrong key, verified hit feedback, 42 guided notes, reconnect");
}
