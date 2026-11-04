#include "../../common/event_wire.h"
HardwareSerial fpgaUart(1);
NimBLECharacteristic* fpgaNotify=nullptr;
QueueHandle_t fpgaCommands=nullptr;
starcluster::Parser fpgaUpstream,fpgaDownstream;
std::atomic<bool> fpgaFailSafe{true};
std::atomic<uint32_t> fpgaLastClient{0};
uint32_t fpgaLastSend=0,fpgaFrames=0;
struct FpgaCommand{uint8_t data[starcluster::FRAME];};
QueueHandle_t padCommands=nullptr;
bool padFailSafe=false,padTurn=true;
bool padSend(const uint8_t*p){FpgaCommand q{};memcpy(q.data,p,sizeof(q.data));if(xQueueSend(padCommands,&q,0)==pdTRUE)return true;padFailSafe=true;return false;}
#include "pad_fpga.h"
PadFpga padFpga(padSend);
bool fpgaAllowed(const uint8_t* p){
    if(p[4]!=3||p[5]>15||p[7]>127||p[8]>127)return false;
    for(int i=18;i<26;i++)if(p[i])return false;
    uint8_t k=p[3];
    return k<=2||(k==4&&p[9]<2)||(k==5&&p[9]<2)||k==6||k==11||k==18||k==19||(k==20&&p[9]==0)||(k==23&&p[9]<=4&&starcluster::u32(p+26)<5);
}
void fpgaPhoneReset(){fpgaFailSafe=true;fpgaUpstream.used=0;}
class FpgaWriteCallbacks:public NimBLECharacteristicCallbacks{
    void onWrite(NimBLECharacteristic* c)override{
        auto v=c->getValue();
        for(uint8_t b:v)if(fpgaUpstream.feed(b)&&fpgaAllowed(fpgaUpstream.data)){
            FpgaCommand q{};memcpy(q.data,fpgaUpstream.data,sizeof(q.data));
            fpgaLastClient=millis();if(xQueueSend(fpgaCommands,&q,0)!=pdTRUE)fpgaFailSafe=true;
        }
    }
} fpgaWriteCallbacks;
void fpgaSetup(NimBLEService* service){
    fpgaCommands=xQueueCreate(32,sizeof(FpgaCommand));
    padCommands=xQueueCreate(64,sizeof(FpgaCommand));
    if(!fpgaCommands||!padCommands){Serial.println("FATAL FPGA_QUEUE");while(true)delay(1000);}
    fpgaUart.setRxBufferSize(4096);fpgaUart.begin(1000000,SERIAL_8N1,5,4);
    auto rx=service->createCharacteristic("4fafc205-1fb5-459e-8fcc-c5c9c331914b",NIMBLE_PROPERTY::WRITE);
    rx->setCallbacks(&fpgaWriteCallbacks);
    fpgaNotify=service->createCharacteristic("4fafc206-1fb5-459e-8fcc-c5c9c331914b",NIMBLE_PROPERTY::NOTIFY);
}
void fpgaLoop(){
    uint32_t now=millis();
    padFpga.tick(now);
    if(phoneConnected&&now-fpgaLastClient.load()>1200){fpgaFailSafe=true;fpgaLastClient=now;}
    if(now-fpgaLastSend>=2){
        uint8_t out[starcluster::GUARDED]={};FpgaCommand q{};bool send=false;
        if(fpgaFailSafe.exchange(false)){xQueueReset(fpgaCommands);starcluster::make(out,2,3);send=true;}
        else if(padFailSafe){padFailSafe=false;xQueueReset(padCommands);padFpga.clear();starcluster::make(out,2,2);send=true;}
        else {
            QueueHandle_t first=padTurn?padCommands:fpgaCommands,second=padTurn?fpgaCommands:padCommands;
            if(xQueueReceive(first,&q,0)==pdTRUE||xQueueReceive(second,&q,0)==pdTRUE){memcpy(out,q.data,sizeof(q.data));send=true;padTurn=!padTurn;
                if(out[4]==2&&out[3]<=1)Serial.printf("PAD_FPGA kind=%u contact=%u note=%u velocity=%u epoch=%lu serial=%lu\n",out[3],out[6],out[7],out[8],(unsigned long)starcluster::u32(out+10),(unsigned long)starcluster::u32(out+14));
            }
        }
        if(send){fpgaUart.write(out,sizeof(out));fpgaLastSend=now;}
    }
    while(fpgaUart.available())if(fpgaDownstream.feed(fpgaUart.read())){
        fpgaFrames++;
        uint8_t* p=fpgaDownstream.data;
        padFpga.receive(p,now);
        if(p[3]==0xa1)Serial.printf("FPGA_ID build=%lu features=%08lX frames=%lu\n",(unsigned long)starcluster::u32(p+6),(unsigned long)starcluster::u32(p+22),(unsigned long)fpgaFrames);
        if(phoneConnected&&fpgaNotify->getSubscribedCount())for(size_t offset=0;offset<starcluster::FRAME;offset+=20){
            size_t n=std::min(size_t(20),starcluster::FRAME-offset);fpgaNotify->notify(p+offset,n);
        }
    }
}
