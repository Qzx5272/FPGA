// BLE control bridge; no audio streaming and no USB Host on ESP32-C3.
#include <Arduino.h>
#include <NimBLEDevice.h>
#include "../../common/event_wire.h"
using namespace starcluster;
HardwareSerial fpga(1);
static constexpr int FPGA_TX=4,FPGA_RX=5; // ESP pin names, NOT FPGA pin assignments.
static constexpr char SERVICE[]="6e400001-b5a3-f393-e0a9-e50e24dcca9e";
static constexpr char BLE_RX_UUID[]="6e400002-b5a3-f393-e0a9-e50e24dcca9e";
static constexpr char BLE_TX_UUID[]="6e400003-b5a3-f393-e0a9-e50e24dcca9e";
NimBLECharacteristic* notifyChar;
portMUX_TYPE queueMux=portMUX_INITIALIZER_UNLOCKED;
uint8_t queueData[64][GUARDED];uint8_t head=0,tail=0,count=0;
volatile bool connected=false,failSafe=false;
uint32_t lastClient=0,lastPoll=0,lastSend=0,overflowCount=0;
Parser upstream,downstream;
bool allowed(const uint8_t*p){
 // Phone owns seat3; privileged operations (upload/global panic) stay on PC.
 if(p[4]!=3||p[5]>15||p[7]>127||p[8]>127)return false;
 for(int i=18;i<26;i++)if(p[i])return false;
 uint8_t k=p[3];
 return k<=2||(k==4&&p[9]<2)||(k==5&&p[9]<2)||k==6||k==11||k==18||k==19;
}
void enqueue(const uint8_t*p){
 portENTER_CRITICAL(&queueMux);
 if(count==64){overflowCount++;failSafe=true;}
 else {memcpy(queueData[tail],p,FRAME);memset(queueData[tail]+FRAME,0,64);tail=(tail+1)&63;count++;}
 portEXIT_CRITICAL(&queueMux);
}
class RXCallbacks:public NimBLECharacteristicCallbacks{
 void onWrite(NimBLECharacteristic*c)override{
  std::string v=c->getValue();
  for(uint8_t b:v)if(upstream.feed(b)&&allowed(upstream.data)){
   lastClient=millis();enqueue(upstream.data);
  }
 }
};
class ServerCallbacks:public NimBLEServerCallbacks{
 void onConnect(NimBLEServer*)override{connected=true;lastClient=millis();}
 void onDisconnect(NimBLEServer*)override{connected=false;failSafe=true;upstream.used=0;NimBLEDevice::startAdvertising();}
};
void setup(){
 fpga.begin(1000000,SERIAL_8N1,FPGA_RX,FPGA_TX);
 failSafe=true; // Retire notes from an earlier bridge instance before new input.
 NimBLEDevice::init("Starcluster-C3");NimBLEDevice::setMTU(185);
 auto server=NimBLEDevice::createServer();server->setCallbacks(new ServerCallbacks());
 auto service=server->createService(SERVICE);
 auto rx=service->createCharacteristic(BLE_RX_UUID,NIMBLE_PROPERTY::WRITE);rx->setCallbacks(new RXCallbacks());
 notifyChar=service->createCharacteristic(BLE_TX_UUID,NIMBLE_PROPERTY::NOTIFY);
 service->start();auto ad=NimBLEDevice::getAdvertising();ad->addServiceUUID(SERVICE);ad->start();
}
void loop(){
 uint32_t now=millis();uint8_t outgoing[GUARDED];bool send=false;
 if(connected&&now-lastClient>1200){failSafe=true;lastClient=now;}
 if(now-lastSend>=2){
  portENTER_CRITICAL(&queueMux);
  if(failSafe){head=tail=count=0;failSafe=false;make(outgoing,2,3);send=true;}
  else if(count){memcpy(outgoing,queueData[head],GUARDED);head=(head+1)&63;--count;send=true;}
  portEXIT_CRITICAL(&queueMux);
  if(send){fpga.write(outgoing,GUARDED);lastSend=now;}
 }
 // Only client heartbeats refresh the board lease. A dead browser must expire.
 while(fpga.available())if(downstream.feed(fpga.read())&&connected){
  // 20-byte fragments also work before BLE MTU negotiation completes.
  for(size_t offset=0;offset<FRAME;offset+=20){size_t n=min(size_t(20),FRAME-offset);notifyChar->setValue(downstream.data+offset,n);notifyChar->notify();}
 }
 delay(1);
}
