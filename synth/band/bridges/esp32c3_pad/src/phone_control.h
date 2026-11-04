// Phone protocol v1: fixed demo RGB, validated Pocket_004 note mapping, MIDI events.
static const char* PHONE_SERVICE="4fafc201-1fb5-459e-8fcc-c5c9c331914b";
static const char* PHONE_RX="4fafc202-1fb5-459e-8fcc-c5c9c331914b";
static const char* PHONE_STATUS="4fafc203-1fb5-459e-8fcc-c5c9c331914b";
NimBLECharacteristic* phoneStatus=nullptr;
NimBLECharacteristic* phoneEvents=nullptr;
QueueHandle_t phoneCommands;
std::atomic<bool> phoneConnected{false}, phoneReset{false};
#include "fpga_bridge.h"
struct PhoneCommand { uint8_t id,r,g,b,kind,profile,slot,note; };
PhoneCommand currentPhone{};
uint8_t mappingBefore[26]={};
uint32_t mappingBase=0;
uint8_t phoneId=0,phoneResult=0,phonePhase=0,phoneRGB[3]={};
uint8_t lastMidi[3]={},vendorBuffer[2048];
size_t vendorUsed=0;
uint32_t phoneDeadline=0,phoneLastStatus=0;
bool sendConfig(uint8_t,const uint8_t*,size_t);
#include "pad_lesson.h"
void phoneFinish(uint8_t result) {
    if(result==2 && currentPhone.kind==2)lesson.refresh();
    phoneResult=result;phonePhase=0;vendorUsed=0;
    Serial.printf("PHONE_RESULT id=%u result=%u\n",phoneId,result);
}
class PhoneServerCallbacks:public NimBLEServerCallbacks {
    void onConnect(NimBLEServer*) override {phoneConnected=true;phoneReset=true;fpgaPhoneReset();}
    void onDisconnect(NimBLEServer*) override {phoneConnected=false;phoneReset=true;fpgaPhoneReset();NimBLEDevice::startAdvertising();}
} phoneServerCallbacks;
class PhoneRXCallbacks:public NimBLECharacteristicCallbacks {
    void onWrite(NimBLECharacteristic* c) override {
        auto v=c->getValue();
        // Entire command fits minimum ATT payload; never accept partial frames.
        if(v.size()!=8 || uint8_t(v[0])!=0x53 || uint8_t(v[1])!=1 || (uint8_t(v[3])!=1 && uint8_t(v[3])!=2))return;
        uint8_t sum=0;for(unsigned i=0;i<7;i++)sum+=uint8_t(v[i]);
        if(uint8_t(v[7])!=uint8_t(~sum))return;
        PhoneCommand q{};q.id=v[2];q.kind=v[3];
        if(q.kind==1){q.r=v[4];q.g=v[5];q.b=v[6];}
        else {q.profile=v[4];q.slot=v[5];q.note=v[6];if(q.profile>3||q.slot>111||q.note>127)return;}
        xQueueSend(phoneCommands,&q,0);
    }
} phoneRXCallbacks;
void phoneSetup() {
    phoneCommands=xQueueCreate(1,sizeof(PhoneCommand));
    if(!phoneCommands){Serial.println("FATAL phone_queue");while(true)delay(1000);}
    auto server=NimBLEDevice::createServer();server->setCallbacks(&phoneServerCallbacks,false);
    auto service=server->createService(PHONE_SERVICE);
    auto rx=service->createCharacteristic(PHONE_RX,NIMBLE_PROPERTY::WRITE);
    rx->setCallbacks(&phoneRXCallbacks);
    phoneStatus=service->createCharacteristic(PHONE_STATUS,NIMBLE_PROPERTY::READ|NIMBLE_PROPERTY::NOTIFY);
    phoneEvents=service->createCharacteristic("4fafc204-1fb5-459e-8fcc-c5c9c331914b",NIMBLE_PROPERTY::NOTIFY);
    fpgaSetup(service);
    service->start();auto ad=NimBLEDevice::getAdvertising();ad->addServiceUUID(PHONE_SERVICE);ad->setScanResponse(true);ad->start();
}
void phoneMidi(uint8_t s,uint8_t a,uint8_t b,uint32_t ms) {
    if(!phoneConnected || !phoneEvents->getSubscribedCount())return;
    uint8_t p[13]={0x4d,1};memcpy(p+2,&decoded,4);memcpy(p+6,&ms,4);p[10]=s;p[11]=a;p[12]=b;
    phoneEvents->notify(p,sizeof(p));
}
void mappingRead(uint8_t phase) {
    uint8_t data[]={5,uint8_t(mappingBase),uint8_t(mappingBase>>8),0,0,26,0,0};
    phonePhase=phase;phoneDeadline=millis()+4000;
    if(!sendConfig(0x23,data,sizeof(data)))phoneFinish(5);
}
void phoneVendorFrame(uint8_t cmd,const uint8_t* p,size_t n) {
    if(lesson.receive(cmd,p,n))return;
    if(phonePhase==1 && cmd==0x11) {
        static const char model[]="SMC-PAD Pocket_004";
        if(n<sizeof(model)-1 || memcmp(p,model,sizeof(model)-1) || (n>sizeof(model)-1 && p[sizeof(model)-1]!=0)) {phoneFinish(4);return;}
        if(currentPhone.kind==2){mappingRead(4);return;}
        uint8_t data[]={5,0x66,0x24,0,0,3,0,0,phoneRGB[0],phoneRGB[1],phoneRGB[2]};
        phonePhase=2;phoneDeadline=millis()+4000;
        if(!sendConfig(0x22,data,sizeof(data)))phoneFinish(5);
    } else if(phonePhase==2 && cmd==0) {
        if(n!=1||p[0]!=0){phoneFinish(5);return;}
        if(currentPhone.kind==2){mappingRead(5);return;}
        uint8_t data[]={5,0x66,0x24,0,0,3,0,0};
        phonePhase=3;phoneDeadline=millis()+4000;
        if(!sendConfig(0x23,data,sizeof(data)))phoneFinish(5);
    } else if(phonePhase==3 && cmd==0x23) {
        const uint8_t expected[]={5,0x66,0x24,0,0,3,0,0};
        if(n!=11 || memcmp(p,expected,8) || memcmp(p+8,phoneRGB,3))phoneFinish(6);
        else phoneFinish(2);
    } else if((phonePhase==4 || phonePhase==5) && cmd==0x23) {
        uint8_t expected[]={5,uint8_t(mappingBase),uint8_t(mappingBase>>8),0,0,26,0,0};
        if(n!=34 || memcmp(p,expected,8)){phoneFinish(6);return;}
        if(phonePhase==5){phoneFinish(memcmp(p+8,mappingBefore,26)?6:2);return;}
        // Only mode 0 note pads are supported; internal control buttons are excluded.
        if(p[8]!=0 || p[9]>15 || p[10]>127){phoneFinish(4);return;}
        memcpy(mappingBefore,p+8,26);mappingBefore[2]=currentPhone.note;
        uint32_t addr=mappingBase+2;
        uint8_t data[]={5,uint8_t(addr),uint8_t(addr>>8),0,0,1,0,0,currentPhone.note};
        phonePhase=2;phoneDeadline=millis()+4000;
        if(!sendConfig(0x22,data,sizeof(data)))phoneFinish(5);
    }
}
void phoneVendor(const uint8_t* data,size_t size) {
    if(!phonePhase && !lesson.receiving())return;
    for(size_t i=0;i<size;i++) {
        if(vendorUsed>=sizeof(vendorBuffer)){phoneFinish(6);return;}
        vendorBuffer[vendorUsed++]=data[i];
        if(vendorUsed<6)continue;
        size_t n=vendorBuffer[3]|(size_t(vendorBuffer[4])<<8)|(size_t(vendorBuffer[5])<<16);
        if(vendorBuffer[0]!=0 || vendorBuffer[1]!=0x59 || n>sizeof(vendorBuffer)-7){phoneFinish(6);return;}
        if(vendorUsed<n+7)continue;
        uint8_t sum=0;for(size_t j=6;j<n+7;j++)sum+=vendorBuffer[j];
        vendorUsed=0;
        if(sum!=255){phoneFinish(6);return;}
        phoneVendorFrame(vendorBuffer[2],vendorBuffer+6,n);
    }
}
void phoneLoop() {
    if(phoneReset.exchange(false))xQueueReset(phoneCommands);
    if(phonePhase && (!client->isConnected() || int32_t(millis()-phoneDeadline)>=0))phoneFinish(7);
    PhoneCommand q;
    if(!phonePhase && xQueueReceive(phoneCommands,&q,0)==pdTRUE) {
        if(lesson.busy()){phoneId=q.id;phoneFinish(7);return;}
        currentPhone=q;mappingBase=q.profile*2931+q.slot*26;
        phoneId=q.id;if(q.kind==1){phoneRGB[0]=q.r;phoneRGB[1]=q.g;phoneRGB[2]=q.b;}vendorUsed=0;
        if(!client->isConnected() || !configNotify)phoneFinish(3);
        else {phoneResult=1;phonePhase=1;phoneDeadline=millis()+4000;if(!sendConfig(0x11,nullptr,0))phoneFinish(5);}
    }
    if(millis()-phoneLastStatus<200)return;
    phoneLastStatus=millis();
    uint8_t p[20]={0x53,1,uint8_t(client->isConnected()),uint8_t(configNotify),phoneId,phoneResult,phoneRGB[0],phoneRGB[1],phoneRGB[2],lastMidi[0],lastMidi[1],lastMidi[2]};
    uint32_t count=decoded,loss=dropped.load();memcpy(p+12,&count,4);memcpy(p+16,&loss,4);
    phoneStatus->setValue(p,sizeof(p));
    if(phoneConnected)phoneStatus->notify();
}
