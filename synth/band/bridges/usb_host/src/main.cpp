// Teensy4.1 native USB Host port -> second FPGA UART; not an ESP32-C3 sketch.
#include <Arduino.h>
#include <USBHost_t36.h>
#include "../../common/event_wire.h"
using namespace starcluster;
USBHost usb;USBHub hub(usb);MIDIDevice_BigBuffer midi(usb);
struct Note {bool down=false,sent=false,sustained=false;uint8_t pitch=60,velocity=0,part=6;uint32_t epoch=0,serial=0,started=0;};
Note notes[16];Parser parser;uint8_t part=6;uint32_t epoch[16]={},seen[16]={},nextSerial=1,lastSend=0,lastPoll=0;
uint8_t owner[16]={};bool sustain=false,midiSustain=false,pedalSustain=false,wasConnected=false,releasePending=false,capable=false;uint32_t features=0;
uint8_t frames[64][GUARDED];uint8_t head=0,tail=0,count=0;
void push(uint8_t kind,uint8_t p=0,uint8_t contact=0,uint8_t pitch=60,uint8_t velocity=100,uint8_t flags=0,uint32_t ep=0,uint32_t serial=0,uint32_t value=0){
 if(count==64){count=head=tail=0;releasePending=true;for(auto&n:notes)n=Note();return;}
 make(frames[tail],kind,2,p,contact,pitch,velocity,flags,ep,serial,value);tail=(tail+1)&63;++count;
}
void off(uint8_t i){auto&n=notes[i];bool held=n.down;uint8_t previousPart=n.part;n.down=false;if(n.sent)push(1,n.part,i,n.pitch,0,0,n.epoch,n.serial);n=Note();
 if(held){bool remaining=false;for(auto&other:notes)if(other.down&&other.part==previousPart)remaining=true;
  if(!remaining)push(4,previousPart,0,60,100,1);}}
void setSustain(){sustain=midiSustain||pedalSustain;if(!sustain)for(uint8_t i=0;i<16;i++)if(notes[i].sustained)off(i);}
void noteOff(uint8_t channel,uint8_t note,uint8_t velocity);
void noteOn(uint8_t channel,uint8_t note,uint8_t velocity){
 if(note<36||note>51)return;
 uint8_t i=note-36;if(!velocity){noteOff(channel,note,0);return;}
 off(i);if(!capable||(part>=8&&part<=14&&!(features&64))||(part==15&&!(features&32)))return;
 static const uint8_t scale[]={0,2,4,5,7,9,11};
 auto&n=notes[i];n.down=true;n.pitch=60+(i/7)*12+scale[i%7];
 n.velocity=velocity;n.part=part;n.serial=nextSerial++;n.started=millis();push(4,part);
}
void noteOff(uint8_t channel,uint8_t note,uint8_t velocity){if(note<36||note>51)return;auto&n=notes[note-36];if(sustain&&n.down){n.sustained=true;return;}off(note-36);}
void control(uint8_t channel,uint8_t cc,uint8_t value){
 if(cc==64){midiSustain=value>=64;setSustain();return;}
 if(cc==120||cc==123){releasePending=true;for(auto&n:notes)n=Note();return;}
 if(cc==20){for(uint8_t i=0;i<16;i++)off(i);part=(uint16_t(value)*16)/128;return;}
 // CC16 expression,17 bend,18 vowel,19 attack,21 decay,22 sustain,23 release.
 uint8_t flag=cc==16||cc==11?0:cc==17?1:cc==18||cc==74?2:cc==19?4:cc==21?5:cc==22?6:cc==23?7:255;
 if(flag==255||owner[part]!=2||(part==15&&flag!=0))return;
 uint32_t v=flag==1||flag==4||flag==6?uint32_t(value)*129:flag==2?uint32_t(value)*5/128:flag==5||flag==7?value>>3:value;
 push(11,part,0,60,100,flag,epoch[part],0,v);
}
void pitchChange(uint8_t channel,int pitch){if(part!=15&&owner[part]==2)push(11,part,0,60,100,1,epoch[part],0,constrain(pitch+8192,0,16383));}
void afterTouch(uint8_t channel,uint8_t pressure){control(channel,11,pressure);}
void afterTouchPoly(uint8_t channel,uint8_t note,uint8_t pressure){control(channel,11,pressure);}
void setup(){
 Serial.begin(115200);Serial1.begin(1000000);pinMode(2,INPUT_PULLUP);releasePending=true;
 midi.setHandleNoteOn(noteOn);midi.setHandleNoteOff(noteOff);midi.setHandleControlChange(control);
 midi.setHandlePitchChange(pitchChange);midi.setHandleAfterTouch(afterTouch);midi.setHandleAfterTouchPoly(afterTouchPoly);usb.begin();
}
void loop(){
 usb.Task();while(midi.read()){}
 bool connected=bool(midi);if(wasConnected&&!connected){releasePending=true;for(auto&n:notes)n=Note();midiSustain=false;setSustain();capable=false;features=0;}wasConnected=connected;
 // External NO pedal, GPIO2 to GND. Contact debounce20ms; sustain release is safe.
 static bool candidate=false,stable=false;static uint32_t changed=0;bool pedal=digitalRead(2)==LOW;
 if(pedal!=candidate){candidate=pedal;changed=millis();}if(pedal!=stable&&millis()-changed>20){stable=pedal;pedalSustain=pedal;setSustain();}
 while(Serial1.available())if(parser.feed(Serial1.read())){
  auto a=parser.data;uint8_t k=a[3],p=a[5];
  if(k==0xa1){capable=true;features=u32(a+22);}
  if((k==128||k==129||k==144||k==145)&&p<16){owner[p]=a[4];epoch[p]=u32(a+10);seen[p]=millis();}
 }
 uint32_t now=millis();
 for(uint8_t i=0;i<16;i++){auto&n=notes[i];if(n.down&&!n.sent){
  if(owner[n.part]==2&&seen[n.part]>=n.started){n.epoch=epoch[n.part];n.sent=true;push(0,n.part,i,n.pitch,n.velocity,0,n.epoch,n.serial);}
  else if(now-n.started>2000)off(i);
 }}
 // A disconnected USB device must stop refreshing seat2's FPGA lease.
 if(connected&&now-lastPoll>=200){lastPoll=now;push(capable?6:18,part);}
 if(now-lastSend>=2){uint8_t emergency[GUARDED];if(releasePending){releasePending=false;head=tail=count=0;make(emergency,2,2);Serial1.write(emergency,GUARDED);lastSend=now;
   if(connected)for(uint8_t p=0;p<16;p++)if(owner[p]==2)push(4,p,0,60,100,1);}
  else if(count){Serial1.write(frames[head],GUARDED);head=(head+1)&63;--count;lastSend=now;}}
}
