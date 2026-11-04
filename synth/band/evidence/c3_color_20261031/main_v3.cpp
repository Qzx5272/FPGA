// USB-only diagnostic receiver. No FPGA UART/GPIO output and no phone service.
#include <Arduino.h>
#include <NimBLEDevice.h>
#include <esp_system.h>
#include <atomic>
#include <algorithm>
#include "midi_packet.h"

static const char* SERVICE = "03b80e5a-ede8-4b33-a751-6ce34ec4c700";
static const char* MIDI_IO = "7772e5db-3868-4112-a1a9-f2669d106bf3";
struct Packet { uint32_t ms; uint16_t size; uint8_t vendor; uint8_t bytes[244]; };
QueueHandle_t packets;
std::atomic<uint32_t> received{0}, dropped{0};
std::atomic<bool> disconnected{false};
NimBLEClient* client = nullptr;
NimBLERemoteCharacteristic* configWrite = nullptr;
bool configNotify = false;
bool subscribed = false;
uint32_t nextScan = 0, lastStatus = 0, decoded = 0, unsupported = 0;
bool held[16][128] = {};

class Callbacks : public NimBLEClientCallbacks {
    void onDisconnect(NimBLEClient*) override { disconnected = true; }
} callbacks;

void notification(NimBLERemoteCharacteristic*, uint8_t* data, size_t size, bool) {
    received++;
    if (size > sizeof(Packet::bytes)) { dropped++; return; }
    Packet p{}; p.ms = millis(); p.size = size; memcpy(p.bytes, data, size);
    if (xQueueSend(packets, &p, 0) != pdTRUE) dropped++;
}

void configNotification(NimBLERemoteCharacteristic*, uint8_t* data, size_t size, bool) {
    if(size>sizeof(Packet::bytes)) {dropped++;return;}
    Packet p{};p.ms=millis();p.size=size;p.vendor=1;memcpy(p.bytes,data,size);
    if(xQueueSend(packets,&p,0)!=pdTRUE) dropped++;
}

bool sendConfig(uint8_t command,const uint8_t* data,size_t size) {
    if(!client->isConnected()||!configWrite||!configNotify||size>12) {
        Serial.println("CONFIG_NOT_READY");return false;
    }
    uint8_t p[20]={0,0x59,command,uint8_t(size),0,0};uint8_t sum=0;
    for(size_t i=0;i<size;i++){p[6+i]=data[i];sum+=data[i];}
    p[6+size]=~sum;
    Serial.print("CONFIG_TX bytes=");for(size_t i=0;i<size+7;i++)Serial.printf("%02X",p[i]);Serial.println();
    bool ok=configWrite->writeValue(p,size+7,!configWrite->canWriteNoResponse());
    Serial.printf("CONFIG_GATT_WRITE ok=%u\n",ok);return ok;
}

void serialCommands() {
    static char line[100];static size_t used=0;
    while(Serial.available()) {
        char c=Serial.read();if(c=='\r')continue;
        if(c!='\n'){if(used<sizeof(line)-1)line[used++]=c;continue;}
        line[used]=0;used=0;
        if(!strcmp(line,"query")) {sendConfig(0x11,nullptr,0);continue;}
        unsigned region,address,length;char extra;
        unsigned profile,slot,r,g,b;
        if(sscanf(line,"color %u %u %u %u %u %c",&profile,&slot,&r,&g,&b,&extra)==5
            &&profile<4&&slot<112&&r<=255&&g<=255&&b<=255) {
            // Pocket_004 layout verified by readback: four 2931-byte profiles,
            // each begins with 112 x 26-byte records, RGB at record offset 5.
            // This command changes ONLY the three RGB bytes, no other config.
            uint32_t address=profile*2931+slot*26+5;
            uint8_t data[11]={5,uint8_t(address),uint8_t(address>>8),0,0,3,0,0,uint8_t(r),uint8_t(g),uint8_t(b)};
            sendConfig(0x22,data,sizeof(data));continue;
        }
        if(sscanf(line,"read %u %u %u %c",&region,&address,&length,&extra)==3
            &&(region==4||region==5)&&address<65536&&length>=1&&length<=1000&&address+length<=65536) {
            uint8_t data[8]={uint8_t(region),uint8_t(address),uint8_t(address>>8),0,0,uint8_t(length),uint8_t(length>>8),0};
            sendConfig(0x23,data,sizeof(data));continue;
        }
        Serial.println("COMMANDS query | read <region 4/5> <decimal address> <length 1..1000> | color <Pocket_004 profile 0..3> <slot 0..111> <R> <G> <B>");
    }
}

unsigned activeNotes() {
    unsigned count = 0;
    for (auto& channel : held) for (bool note : channel) if (note) count++;
    return count;
}

void reportPacket(const Packet& p) {
    if(p.vendor) {
        Serial.printf("CONFIG_RX ms=%lu bytes=",(unsigned long)p.ms);
        for(unsigned i=0;i<p.size;i++)Serial.printf("%02X",p.bytes[i]);Serial.println();return;
    }
    Serial.printf("RAW ms=%lu bytes=", (unsigned long)p.ms);
    for (unsigned i=0; i<p.size; i++) Serial.printf("%02X", p.bytes[i]);
    Serial.println();
    // Validate first so unsupported packets cannot partially alter held notes.
    if (!decodeMidiPacket(p.bytes,p.size,[](uint8_t,uint8_t,uint8_t,uint16_t){})) {
        unsupported++; Serial.println("UNSUPPORTED_OR_MALFORMED raw_preserved=1"); return;
    }
    decodeMidiPacket(p.bytes,p.size,[&](uint8_t s,uint8_t a,uint8_t b,uint16_t ts){
        uint8_t channel=s&15, kind=s&0xf0; const char* name="OTHER";
        if (s>=0xf8) { name="REALTIME"; if(s==0xff) memset(held,0,sizeof(held)); }
        else if(kind==0x90 && b) {name="NOTE_ON"; held[channel][a]=true;}
        else if(kind==0x80 || kind==0x90) {name="NOTE_OFF"; held[channel][a]=false;}
        else if(kind==0xa0) name="POLY_PRESSURE";
        else if(kind==0xb0) {name="CC"; if(a==120||a==123) memset(held[channel],0,sizeof(held[channel]));}
        else if(kind==0xc0) name="PROGRAM";
        else if(kind==0xd0) name="CHANNEL_PRESSURE";
        else if(kind==0xe0) name="PITCH_BEND";
        decoded++;
        Serial.printf("MIDI ms=%lu ts=%u type=%s channel=%u data1=%u data2=%u active=%u\n",
            (unsigned long)p.ms,ts,name,channel+1,a,b,activeNotes());
    });
}

void connectPad() {
    Serial.println("SCAN seconds=3 target=SMC-PAD");
    auto scan=NimBLEDevice::getScan();
    auto results=scan->start(3,false);
    for(int i=0;i<results.getCount();i++) {
        auto device=results.getDevice(i);
        std::string name=device.getName();
        std::string upper=name;
        std::transform(upper.begin(),upper.end(),upper.begin(),[](unsigned char c){return toupper(c);});
        bool midi=device.isAdvertisingService(NimBLEUUID(SERVICE));
        bool match=upper.find("SMC")!=std::string::npos && upper.find("PAD")!=std::string::npos;
        if(midi||match) Serial.printf("CANDIDATE name=%s address=%s rssi=%d midi_service=%u\n",
            name.c_str(),device.getAddress().toString().c_str(),device.getRSSI(),midi);
        // Do not connect indiscriminately to other nearby MIDI instruments.
        if(!match) continue;
        Serial.printf("CONNECT name=%s address=%s\n",name.c_str(),device.getAddress().toString().c_str());
        disconnected=false;
        if(!client->connect(&device)) {Serial.println("CONNECT_FAILED");break;}
        auto service=client->getService(SERVICE);
        auto characteristic=service?service->getCharacteristic(MIDI_IO):nullptr;
        if(!characteristic || !characteristic->canNotify()) {
            Serial.println("MIDI_SERVICE_OR_NOTIFY_MISSING");client->disconnect();break;
        }
        if(!characteristic->subscribe(true,notification)) {
            Serial.println("SUBSCRIBE_FAILED");client->disconnect();break;
        }
        subscribed=true;
        auto vendorService=client->getService(NimBLEUUID(uint16_t(0xae40)));
        configWrite=vendorService?vendorService->getCharacteristic(NimBLEUUID(uint16_t(0xae41))):nullptr;
        auto configRx=vendorService?vendorService->getCharacteristic(NimBLEUUID(uint16_t(0xae42))):nullptr;
        configNotify=configRx&&configRx->canNotify()&&configRx->subscribe(true,configNotification);
        Serial.printf("CONFIG_SERVICE present=%u write=%u write_no_response=%u notify=%u\n",
            vendorService!=nullptr,configWrite&&configWrite->canWrite(),configWrite&&configWrite->canWriteNoResponse(),configNotify);
        Serial.println("READY BLE_MIDI_SUBSCRIBED press_and_release_pads FPGA_OUTPUT_DISABLED");
        break;
    }
    scan->clearResults(); nextScan=millis()+2000;
}

void setup() {
    Serial.begin(115200);
    delay(1500);
    Serial.printf("BOOT firmware=c3-pad-monitor-v3-color reset_reason=%d FPGA_OUTPUT_DISABLED\n",esp_reset_reason());
    packets=xQueueCreate(128,sizeof(Packet));
    if(!packets) {Serial.println("FATAL queue_allocation");while(true) delay(1000);}
    NimBLEDevice::init("Starcluster-Pad-Monitor");
    NimBLEDevice::setMTU(185);
    auto scan=NimBLEDevice::getScan();scan->setActiveScan(true);scan->setInterval(80);scan->setWindow(60);
    client=NimBLEDevice::createClient();client->setClientCallbacks(&callbacks,false);
    client->setConnectTimeout(5);client->setConnectionParams(6,12,0,200);
}

void loop() {
    if(disconnected.exchange(false)) {
        subscribed=false;memset(held,0,sizeof(held));xQueueReset(packets);
        configWrite=nullptr;configNotify=false;
        Serial.println("DISCONNECTED active_notes_cleared=1");nextScan=millis()+1000;
    }
    Packet p;
    while(xQueueReceive(packets,&p,0)==pdTRUE) reportPacket(p);
    serialCommands();
    if(!client->isConnected() && int32_t(millis()-nextScan)>=0) connectPad();
    if(millis()-lastStatus>=3000) {
        lastStatus=millis();
        Serial.printf("STATUS uptime_ms=%lu connected=%u subscribed=%u packets=%lu decoded=%lu dropped=%lu unsupported=%lu active=%u free_heap=%u\n",
            (unsigned long)millis(),client->isConnected(),subscribed,(unsigned long)received.load(),
            (unsigned long)decoded,(unsigned long)dropped.load(),(unsigned long)unsupported,activeNotes(),ESP.getFreeHeap());
    }
    delay(2);
}
