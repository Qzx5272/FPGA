"""Exercise actual Teensy callbacks and disconnect loop with host-side IO stubs."""
from pathlib import Path
import json,shutil,subprocess
band=Path(__file__).resolve().parents[1]
out=Path('D:/StarclusterBuilds/teensy_behavior');out.mkdir(exist_ok=True)
(out/'Arduino.h').write_text('''#pragma once
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
inline uint32_t nowMs=1000;
inline uint32_t millis(){return nowMs;}
inline void delay(unsigned n){nowMs+=n;}
constexpr int INPUT_PULLUP=2,LOW=0;
inline void pinMode(int,int){}
inline int digitalRead(int){return 1;}
template<class T>T constrain(T v,T a,T b){return std::min(b,std::max(a,v));}
struct MockSerial{
 std::vector<uint8_t> out;
 void begin(unsigned){}
 int available(){return 0;}
 int read(){return -1;}
 void write(const uint8_t*p,unsigned n){out.insert(out.end(),p,p+n);}
};
inline MockSerial Serial,Serial1;
''')
(out/'USBHost_t36.h').write_text('''#pragma once
struct USBHost{void begin(){}void Task(){}};
struct USBHub{USBHub(USBHost&){}};
struct MIDIDevice_BigBuffer{
 bool connected=true;MIDIDevice_BigBuffer(USBHost&){}
 explicit operator bool()const{return connected;}bool read(){return false;}
 template<class T>void setHandleNoteOn(T){}
 template<class T>void setHandleNoteOff(T){}
 template<class T>void setHandleControlChange(T){}
 template<class T>void setHandlePitchChange(T){}
 template<class T>void setHandleAfterTouch(T){}
 template<class T>void setHandleAfterTouchPoly(T){}
};
''')
source=(band/'bridges/usb_host/src/main.cpp').as_posix()
(out/'test.cpp').write_text('#include "'+source+'"\n'+r'''
#include <cassert>
#include <iostream>
int main(){
 setup();assert(releasePending);loop();assert(!releasePending&&Serial1.out[3]==2);
 capable=true;features=64;part=6;owner[6]=2;epoch[6]=9;seen[6]=nowMs;
 noteOn(1,36,99);loop();assert(notes[0].down&&notes[0].sent);
 uint32_t first=notes[0].serial;
 control(1,64,127);noteOn(1,36,0);assert(notes[0].sustained&&notes[0].down);
 pedalSustain=true;setSustain();control(1,64,0);assert(notes[0].down);
 pedalSustain=false;setSustain();assert(!notes[0].down);
 assert(count&&frames[(tail+63)&63][3]==4&&frames[(tail+63)&63][9]==1);
 noteOn(1,36,97);assert(notes[0].serial!=first);loop();noteOff(1,36,0);assert(!notes[0].down);
 noteOn(1,37,80);control(1,123,0);assert(releasePending&&!notes[1].down);
 head=tail=count=0;releasePending=false;features=32;control(1,20,127);assert(part==15);
 owner[15]=2;epoch[15]=10;seen[15]=nowMs;noteOn(1,36,80);assert(notes[0].down&&notes[0].part==15);
 auto before=count;control(1,74,127);pitchChange(1,1000);assert(count==before);off(0);part=6;
 releasePending=false;head=tail=count=0;lastPoll=lastSend=0;Serial1.out.clear();
 midi.connected=false;wasConnected=true;capable=true;features=64;nowMs=2000;loop();
 assert(!capable&&features==0&&count==0&&Serial1.out.size()==GUARDED&&Serial1.out[3]==2);
 auto sent=Serial1.out.size();nowMs+=1000;loop();assert(count==0&&Serial1.out.size()==sent);
 midi.connected=true;nowMs+=1000;loop();assert(Serial1.out.size()==sent+GUARDED&&Serial1.out[sent+3]==18);
 std::cout<<"PASS actual USB bridge: zero-velocity sustain, dual pedals, fresh serial, last-note return, singer role, CC123, unplug lease expiry, reconnect identity\n";
}
''')
logs=[]
for command in ([shutil.which('g++'),'-std=c++17','-I',str(out),str(out/'test.cpp'),'-o',str(out/'test.exe')],[str(out/'test.exe')]):
 p=subprocess.run(command,capture_output=True,text=True,timeout=45);logs.append(dict(returncode=p.returncode,output=p.stdout+p.stderr))
 if p.returncode:break
passed=len(logs)==2 and all(p['returncode']==0 for p in logs) and 'PASS actual USB bridge' in logs[1]['output']
result=dict(status='passed' if passed else 'failed',scope='Actual firmware callbacks with mocked serial/USB IO; not physical USB enumeration',logs=logs)
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if not passed:raise SystemExit(1)
