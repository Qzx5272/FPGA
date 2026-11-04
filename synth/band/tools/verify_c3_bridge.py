"""Check actual C3 bridge callbacks/loop with mock BLE and serial transports."""
from pathlib import Path
import json,shutil,subprocess
band=Path(__file__).resolve().parents[1];out=Path('D:/StarclusterBuilds/c3_behavior');out.mkdir(exist_ok=True)
(out/'Arduino.h').write_text('''#pragma once
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>
#include <algorithm>
using std::min;
inline uint32_t nowMs=1000;
inline uint32_t millis(){return nowMs;}inline void delay(unsigned n){nowMs+=n;}
using portMUX_TYPE=int;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portENTER_CRITICAL(x) do{}while(0)
#define portEXIT_CRITICAL(x) do{}while(0)
constexpr int SERIAL_8N1=1;
struct HardwareSerial{
 std::vector<uint8_t> out,in;HardwareSerial(int){}
 void begin(unsigned,int,int,int){}
 int available(){return in.size();}
 int read(){auto b=in.front();in.erase(in.begin());return b;}
 void write(const uint8_t*p,unsigned n){out.insert(out.end(),p,p+n);}
};
''')
(out/'NimBLEDevice.h').write_text('''#pragma once
#include <string>
#include <vector>
struct NimBLECharacteristic;struct NimBLEServer;
struct NimBLECharacteristicCallbacks{virtual void onWrite(NimBLECharacteristic*){}};
struct NimBLEServerCallbacks{virtual void onConnect(NimBLEServer*){}virtual void onDisconnect(NimBLEServer*){}};
struct NimBLECharacteristic{
 std::string value;std::vector<std::string> notices;
 std::string getValue(){return value;}void setCallbacks(NimBLECharacteristicCallbacks*){}
 void setValue(const uint8_t*p,size_t n){value.assign((const char*)p,n);}
 bool notify(){notices.push_back(value);return true;}
};
struct NimBLEService{NimBLECharacteristic*createCharacteristic(const char*,int){return new NimBLECharacteristic;}void start(){}};
struct NimBLEServer{void setCallbacks(NimBLEServerCallbacks*){}NimBLEService*createService(const char*){return new NimBLEService;}};
struct NimBLEAdvertising{void addServiceUUID(const char*){}void start(){}};
struct NimBLEDevice{
 static void init(const char*){}static void setMTU(int){}static NimBLEServer*createServer(){return new NimBLEServer;}
 static NimBLEAdvertising*getAdvertising(){static NimBLEAdvertising a;return &a;}static void startAdvertising(){}
};
namespace NIMBLE_PROPERTY{constexpr int WRITE=1,NOTIFY=2;}
''')
source=(band/'bridges/esp32c3/src/main.cpp').as_posix()
(out/'test.cpp').write_text('#include "'+source+'"\n'+r'''
#include <cassert>
#include <iostream>
int main(){
 setup();assert(failSafe);loop();assert(!failSafe&&fpga.out[3]==2);fpga.out.clear();lastSend=0;uint8_t frame[GUARDED];
 make(frame,5,3,0,0,60,100,0);assert(allowed(frame));
 make(frame,5,3,0,0,60,100,1);assert(allowed(frame));
 make(frame,127,3);assert(!allowed(frame));make(frame,13,3);assert(!allowed(frame));
 make(frame,4,3,0,0,60,100,2);assert(!allowed(frame));make(frame,0,2);assert(!allowed(frame));
 make(frame,0,3);RXCallbacks rx;NimBLECharacteristicCallbacks*callback=&rx;NimBLECharacteristic c;
 c.value.assign((const char*)frame,20);callback->onWrite(&c);assert(count==0);
 c.value.assign((const char*)frame+20,FRAME-20);callback->onWrite(&c);assert(count==1);
 connected=true;lastClient=nowMs;loop();assert(fpga.out.size()==GUARDED&&fpga.out[3]==0);
 auto sent=fpga.out.size();nowMs+=400;loop();assert(fpga.out.size()==sent);
 nowMs+=1000;loop();assert(fpga.out.size()==sent+GUARDED&&fpga.out[sent+3]==2&&fpga.out[sent+4]==3);
 lastClient=nowMs;make(frame,0,3);for(int i=0;i<65;i++)enqueue(frame);assert(failSafe&&overflowCount==1);
 nowMs+=3;loop();assert(count==0&&!failSafe&&fpga.out[fpga.out.size()-GUARDED+3]==2);
 make(frame,18,3);fpga.in.assign(frame,frame+FRAME);loop();assert(notifyChar->notices.size()==2);
 assert(notifyChar->notices[0].size()==20&&notifyChar->notices[1].size()==14);
 std::string reply=notifyChar->notices[0]+notifyChar->notices[1];assert(reply==std::string((const char*)frame,FRAME));
 ServerCallbacks server;NimBLEServerCallbacks*serverCallback=&server;serverCallback->onDisconnect(nullptr);assert(!connected&&failSafe);nowMs+=3;loop();assert(!failSafe&&count==0);
 std::cout<<"PASS actual C3 bridge: seat filtering, transport, fragmented GATT, no synthetic lease heartbeat, timeout release, overflow release, notify chunks, disconnect\n";
}
''')
logs=[]
for command in ([shutil.which('g++'),'-std=c++17','-I',str(out),str(out/'test.cpp'),'-o',str(out/'test.exe')],[str(out/'test.exe')]):
 p=subprocess.run(command,capture_output=True,text=True,timeout=45);logs.append(dict(returncode=p.returncode,output=p.stdout+p.stderr))
 if p.returncode:break
passed=len(logs)==2 and all(p['returncode']==0 for p in logs) and 'PASS actual C3 bridge' in logs[1]['output']
result=dict(status='passed' if passed else 'failed',scope='Actual C3 firmware callbacks with mocked GATT and serial; no BLE radio pairing or throughput claim',logs=logs)
(out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if not passed:raise SystemExit(1)
