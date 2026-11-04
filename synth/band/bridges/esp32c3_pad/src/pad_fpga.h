#pragma once
#include "../../common/event_wire.h"
// Independent seat 2, plucked-string part 8. Physical MIDI identity is retained.
struct PadFpga {
 static constexpr uint8_t SOURCE=2,PART=8;
 uint8_t part=PART;int8_t octave=0;bool sustain=false,configRequired=false,configKnown=false;
 struct TakeEvent{uint32_t ms;uint8_t kind,contact,pitch,velocity;};
 TakeEvent take[512]{};uint16_t takeCount=0,takeIndex=0;uint8_t takePart=PART;
 bool lessonRequested=false,scoreGuide=false;bool scorePlaying=false;uint8_t scoreIndex=0,cue=0;uint16_t cueTag=0;
 bool recording=false,replaying=false,takeFull=false,countersKnown=false;
 uint8_t recordCounter=0,replayCounter=0;uint32_t nowMs=0,takeStart=0,replayStart=0,takeDuration=0;
 uint8_t haltCounter=0;bool haltKnown=false;
 uint32_t replaySerial[32]{};
 using Send=bool(*)(const uint8_t*);
 struct Note {bool held=false,sent=false;uint8_t channel=0,key=0,velocity=0,pitch=0,part=PART;uint32_t epoch=0,serial=0,at=0;};
 Note notes[32]{};Send send;bool enabled=false,online=false;uint8_t owner=0;
 uint32_t epoch=0,serial=0,lastReply=0,lastPoll=0,lastIdentity=0;
 explicit PadFpga(Send s):send(s){}
 void capture(uint8_t kind,uint8_t contact,uint8_t pitch,uint8_t velocity){
  if(!recording||kind>2)return;
  if(takeCount==512){recording=false;takeFull=true;takeDuration=nowMs-takeStart;return;}
  take[takeCount++]={uint32_t(nowMs-takeStart),kind,contact,pitch,velocity};
 }
 void finishTake(){if(recording){takeDuration=nowMs-takeStart;recording=false;}}
 void cancelReplay(){if(replaying){replaying=false;event(2);}}
 void takeCommand(uint8_t rec,uint8_t replay){
  if(!countersKnown){recordCounter=rec;replayCounter=replay;countersKnown=true;return;}
  if(rec!=recordCounter){recordCounter=rec;cancelReplay();
   if(recording)finishTake();else{release();takeCount=0;takeFull=false;takePart=part;takeStart=nowMs;recording=true;}
  }
  if(replay!=replayCounter){replayCounter=replay;finishTake();cancelReplay();
   if(takeCount&&part==takePart&&online&&owner==SOURCE){release();owner=SOURCE;replaying=true;takeIndex=0;replayStart=nowMs;for(auto &n:replaySerial)n=0;}
  }
 }
 bool event(uint8_t kind,uint8_t contact=0,uint8_t pitch=60,uint8_t velocity=100,uint32_t e=0,uint32_t seq=0){
  uint8_t p[starcluster::GUARDED];starcluster::make(p,kind,SOURCE,part,contact,pitch,velocity,0,e,seq);
  bool ok=send(p);if(ok)capture(kind,contact,pitch,velocity);return ok;
 }
 void clear(){for(auto &n:notes)n=Note{};owner=0;}
 void release(){event(2);clear();}
 void connect(bool value){finishTake();cancelReplay();enabled=value;lessonRequested=false;scoreGuide=false;scorePlaying=false;cue=0;online=false;configKnown=false;countersKnown=false;haltKnown=false;sustain=false;clear();event(2);lastPoll=lastIdentity=0;}
 void start(unsigned i){auto &n=notes[i];if(!n.held||n.sent||!online||owner!=SOURCE||(configRequired&&!configKnown))return;
  n.epoch=epoch;n.serial=++serial;n.part=part;n.sent=event(0,i,n.pitch,n.velocity,n.epoch,n.serial);
 }
 void off(unsigned i){auto &n=notes[i];if(n.sent){uint8_t p[starcluster::GUARDED];starcluster::make(p,1,SOURCE,n.part,i,n.pitch,0,0,n.epoch,n.serial);if(send(p))capture(1,i,n.pitch,0);}n=Note{};}
 // Every consecutive bank of 16 pad IDs lights 16 different display cells.
 static int padPitch(uint8_t key){return key<48?60+((key+8)&15):key;}
 void configure(uint8_t nextPart,int8_t nextOctave,bool nextSustain){
  if(nextPart>15||nextOctave< -3||nextOctave>4)return;
  if(nextPart!=part){
   finishTake();cancelReplay();
   release();uint8_t p[starcluster::GUARDED];starcluster::make(p,4,SOURCE,part,0,60,100,1);send(p);
   part=nextPart;owner=0;epoch=0;
  }
  if(sustain&&!nextSustain)for(unsigned i=0;i<32;i++)if(notes[i].sent&&!notes[i].held)off(i);
  octave=nextOctave;sustain=nextSustain;
  if(!configKnown)for(auto &n:notes)if(n.held&&!n.sent){
   int pitch=padPitch(n.key);if(part>=3)pitch+=int(octave)*12;
   n.pitch=pitch<0?0:pitch>127?127:pitch;
  }
  configKnown=true;
 }
 void midi(uint8_t status,uint8_t key,uint8_t velocity,uint32_t now,bool exact=false){
  nowMs=now;
  if(!enabled)return;
  uint8_t ch=status&15,kind=status&240;
  if(status==255||kind==128||kind==144||(kind==176&&(key==120||key==123)))cancelReplay();
  if(status==255){release();return;}
  if(kind==176&&(key==120||key==123)){for(unsigned i=0;i<32;i++)if((notes[i].held||notes[i].sent)&&notes[i].channel==ch)off(i);return;}
  if(kind!=128&&kind!=144)return;
  int found=-1,free=-1;
  for(unsigned i=0;i<32;i++){if((notes[i].held||notes[i].sent)&&notes[i].channel==ch&&notes[i].key==key)found=i;if(!notes[i].held&&!notes[i].sent&&free<0)free=i;}
  if(kind==128||!velocity){if(found>=0){if(sustain&&notes[found].sent&&notes[found].part>=3)notes[found].held=false;else off(found);}return;}
  if(found>=0){off(found);free=found;}
  if(free<0){release();return;}
  auto &n=notes[free];n.held=true;n.channel=ch;n.key=key;n.velocity=velocity;
  // Pocket presets can emit pad IDs 0..15 or 24..39, not musical pitches.
  // Normalize low IDs into MIDI 60..75; retain explicitly pitched notes >=48.
  int pitch=exact?key:padPitch(key);if(!exact&&part>=3)pitch+=int(octave)*12;
  n.pitch=pitch<0?0:pitch>127?127:pitch;n.at=now;
  start(free);
 }
 void receive(const uint8_t*p,uint32_t now){
  nowMs=now;
  if(p[3]==161){uint32_t features=starcluster::u32(p+22);online=(features&4096)!=0;configRequired=(features&8192)!=0;lastReply=now;}
  if(p[3]==163&&configRequired){
   if(haltKnown&&haltCounter!=p[10]){finishTake();cancelReplay();release();}
   haltCounter=p[10];haltKnown=true;
   bool nextPlaying=p[11]==0xb5&&(p[15]&8);uint8_t nextSong=p[15]&7;
   if(scorePlaying!=nextPlaying||scoreIndex!=nextSong){for(unsigned i=0;i<32;++i)if(notes[i].held||notes[i].sent)off(i);}
   scorePlaying=nextPlaying;scoreIndex=nextSong;scoreGuide=p[11]==0xb5;cue=p[12];cueTag=uint16_t(p[13])|(uint16_t(p[14])<<8);
   bool learning=p[7]==3;
   if(learning!=lessonRequested){finishTake();cancelReplay();release();}
   lessonRequested=learning;
   configure(learning&&!scoreGuide?8:p[4],learning?0:int8_t(p[5]),!learning&&(p[6]&1));
   if(!learning)takeCommand(p[8],p[9]);lastReply=now;
  }
  if((p[3]==128||p[3]==129)&&p[5]==part){
   lastReply=now;uint32_t next=starcluster::u32(p+10);
   if(owner==SOURCE&&(p[4]!=SOURCE||epoch!=next)){finishTake();cancelReplay();clear();}
   owner=p[4];epoch=next;
   for(unsigned i=0;i<32;i++)start(i);
  }
 }
 void tick(uint32_t now){
  nowMs=now;
  if(!enabled)return;
  if(online&&uint32_t(now-lastReply)>1000){
   finishTake();cancelReplay();release();online=false;
   configKnown=false;countersKnown=false;haltKnown=false;
  }
  if(replaying){
   if(!online||owner!=SOURCE||part!=takePart)cancelReplay();
   else if(takeIndex<takeCount&&uint32_t(now-replayStart)>=take[takeIndex].ms){
    auto &e=take[takeIndex];uint8_t p[starcluster::GUARDED];
    if(e.kind==0&&replaySerial[e.contact]==0)replaySerial[e.contact]=++serial;
    starcluster::make(p,e.kind,SOURCE,part,e.contact,e.pitch,e.velocity,0,epoch,replaySerial[e.contact]);
    if(send(p)){if(e.kind==1)replaySerial[e.contact]=0;takeIndex++;}
   }else if(takeIndex==takeCount&&uint32_t(now-replayStart)>=takeDuration)cancelReplay();
  }
  for(auto &n:notes)if(n.held&&!n.sent&&uint32_t(now-n.at)>300)n=Note{};
  if(uint32_t(now-lastIdentity)>=2000){event(18);lastIdentity=now;}
  if(uint32_t(now-lastPoll)>=100){
   if(online&&owner==0)event(4);
   event(6);if(configRequired){event(20);uint8_t p[starcluster::GUARDED];
    starcluster::make(p,21,SOURCE,part,0,60,100,(recording?1:0)|(replaying?2:0)|(takeFull?4:0)|(takeCount?8:0));send(p);
   }lastPoll=now;
  }
 }
};
