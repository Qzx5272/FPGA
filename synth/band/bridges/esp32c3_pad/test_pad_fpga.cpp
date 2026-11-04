#include <vector>
#include <array>
#include <cassert>
#include <cstdio>
#include "src/pad_fpga.h"
std::vector<std::array<uint8_t,34>> frames;
bool send(const uint8_t*p){assert(starcluster::valid(p));std::array<uint8_t,34>a;memcpy(a.data(),p,34);frames.push_back(a);return true;}
void reply(PadFpga&b,uint8_t owner,uint32_t epoch,uint32_t now){uint8_t p[98];starcluster::make(p,128,owner,8,0,60,100,0,epoch);b.receive(p,now);}
int main(){PadFpga b(send);b.connect(true);uint8_t p[98];starcluster::make(p,161,0);starcluster::put32(p+22,4096);b.receive(p,10);
 b.midi(144,24,90,11);b.midi(128,24,0,12);reply(b,2,7,13);assert(frames.size()==1);
 b.midi(144,24,35,14);assert(frames.back()[3]==0&&frames.back()[7]==60&&frames.back()[8]==35);auto on=frames.back();
 b.midi(144,25,110,15);assert(frames.back()[6]!=on[6]);b.midi(144,24,0,16);auto off=frames.back();assert(off[3]==1&&off[6]==on[6]&&starcluster::u32(off.data()+10)==7&&starcluster::u32(off.data()+14)==starcluster::u32(on.data()+14));
 b.midi(176,123,0,17);assert(frames.back()[3]==1);for(auto n:b.notes)assert(!n.held);
 reply(b,3,8,18);auto count=frames.size();b.midi(144,26,127,19);assert(frames.size()==count);b.tick(400);reply(b,2,9,401);assert(frames.back()[3]!=0);
 b.midi(144,27,127,402);b.connect(false);assert(frames.back()[3]==2);count=frames.size();b.midi(144,28,127,403);b.tick(3000);assert(frames.size()==count);
 b.connect(true);b.receive(p,4000);reply(b,2,10,4001);b.midi(144,29,80,4002);b.tick(5102);assert(!b.online);for(auto n:b.notes)assert(!n.held);
 b.receive(p,6000);reply(b,2,11,6001);
 for(uint8_t key: {uint8_t(0),uint8_t(7),uint8_t(10),uint8_t(11),uint8_t(15),uint8_t(24),uint8_t(39),uint8_t(60)}){
  b.midi(153,key,100,6002);assert(frames.back()[3]==0);assert(frames.back()[7]==(key<48?60+((key+8)&15):key));b.midi(137,key,0,6003);assert(frames.back()[3]==1);
 }
 for(int first=0;first<=32;++first){
  unsigned cells=0;
  for(int key=first;key<first+16;++key){
   b.midi(153,key,85,6008);auto played=frames.back();
   assert(played[3]==0&&played[7]>=60&&played[7]<=75);
   cells|=1u<<(played[7]-60);b.midi(137,key,0,6009);assert(frames.back()[3]==1);
  }
  assert(cells==65535);
 }
 b.configure(8,0,true);b.midi(144,60,100,6100);auto sustained=frames.back();count=frames.size();
 b.midi(128,60,0,6101);assert(frames.size()==count);
 b.configure(8,2,true);b.configure(8,2,false);off=frames.back();
 assert(off[3]==1&&off[7]==60&&off[5]==8&&starcluster::u32(off.data()+14)==starcluster::u32(sustained.data()+14));
 b.midi(144,60,100,6102);assert(frames.back()[7]==84);b.configure(8,-3,false);b.midi(128,60,0,6103);assert(frames.back()[7]==84);
 b.configure(8,0,true);b.midi(144,61,100,6104);b.midi(128,61,0,6105);b.midi(176,123,0,6106);assert(frames.back()[3]==1);
 for(auto n:b.notes)assert(!n.sent&&!n.held);
 b.midi(144,62,100,6107);b.midi(128,62,0,6108);count=frames.size();b.midi(144,62,100,6109);
 assert(frames.size()==count+2&&frames[count][3]==1&&frames[count+1][3]==0);
 b.configure(4,0,false);assert(b.part==4&&b.owner==0);assert(frames.back()[3]==4&&frames.back()[5]==8&&frames.back()[9]==1);
 PadFpga fresh(send);fresh.connect(true);starcluster::make(p,161,0);starcluster::put32(p+22,4096|8192);fresh.receive(p,7000);reply(fresh,2,12,7001);
 count=frames.size();fresh.midi(144,60,100,7002);assert(frames.size()==count);
 starcluster::make(p,163,8,1,1);fresh.receive(p,7003);assert(fresh.configKnown&&fresh.octave==1&&fresh.sustain);
 PadFpga recorder(send);recorder.connect(true);recorder.receive(p,8000);recorder.online=true;recorder.configure(8,0,false);reply(recorder,2,30,8000);
 recorder.takeCommand(0,0);recorder.takeCommand(1,0);assert(recorder.recording);reply(recorder,2,30,8001);
 recorder.midi(144,60,110,8010);auto recordedOn=frames.back();recorder.midi(128,60,0,8030);
 recorder.nowMs=8040;recorder.takeCommand(2,0);assert(!recorder.recording&&recorder.takeCount==2);
 recorder.takeCommand(2,1);assert(recorder.replaying);count=frames.size();recorder.tick(8050);
 assert(frames.size()>=count+1);auto replayOn=frames[count];assert(replayOn[3]==0&&replayOn[7]==60&&starcluster::u32(replayOn.data()+14)!=starcluster::u32(recordedOn.data()+14));
 recorder.tick(8070);assert(frames.back()[3]==1);assert(starcluster::u32(frames.back().data()+14)==starcluster::u32(replayOn.data()+14));
 recorder.tick(8080);assert(!recorder.replaying&&frames.back()[3]==2);
 recorder.owner=2;recorder.takeCommand(2,2);assert(recorder.replaying);recorder.midi(248,0,0,8081);assert(recorder.replaying);
 recorder.midi(144,62,100,8082);assert(!recorder.replaying);
 recorder.takeCommand(3,2);for(int i=0;i<513;i++)recorder.capture(0,0,60,100);assert(recorder.takeFull&&!recorder.recording&&recorder.takeCount==512);
 recorder.configRequired=true;recorder.haltKnown=true;recorder.haltCounter=0;recorder.replaying=true;
 starcluster::make(p,163,8,0,0);p[8]=3;p[9]=2;p[10]=1;recorder.receive(p,8090);
 assert(!recorder.replaying&&!recorder.recording&&recorder.haltCounter==1);
 recorder.online=true;recorder.configKnown=true;recorder.countersKnown=true;recorder.haltKnown=true;recorder.lastReply=8090;
 recorder.tick(9200);assert(!recorder.online&&!recorder.configKnown&&!recorder.countersKnown&&!recorder.haltKnown);
 recorder.takeCommand(0,0);assert(!recorder.recording&&!recorder.replaying);
 puts("PASS: ownership, identity, disconnect, sustain/release/retrigger, octave, part, CC, config, timed take replay with fresh identities, live override, bounded capture");}
