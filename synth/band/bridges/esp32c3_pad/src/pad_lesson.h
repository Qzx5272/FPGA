#pragma once
#include "rehearsal_pads.h"
// Pocket_004 profile 4, bank 2: RGB triplets and the factory upper-pad control overrides.
class PadLesson {
    enum Phase { Offline, Model, Records, Controls, ControlsAck, Ready, Ack, Verify, Fault } phase=Offline;
    enum { count=16, base=3*2931+16*26 };
    static constexpr uint8_t melody[]={
        0,0,4,4,5,5,4,3,3,2,2,1,1,0,4,4,3,3,2,2,1,
        4,4,3,3,2,2,1,0,0,4,4,5,5,4,3,3,2,2,1,1,0};
    static constexpr uint8_t scale[]={60,62,64,65,67,69};
    uint8_t keys[count]{},channels[count]{},index=0,cursor=0,step=0,pitch=0;
    uint32_t shown[count]{},pulseUntil[count]{},outgoing=0,deadline=0,offAt=0;
    bool held[count]{},pulse[count]{},learning=false,pendingHit=false;
    static bool due(uint32_t end){return int32_t(millis()-end)>=0;}
    bool wanted() const{return padFpga.online && padFpga.configKnown && padFpga.lessonRequested;}
    void releaseNote(){if(pitch){padFpga.midi(0x89,pitch,0,millis());pitch=0;}}
    void fail(){phase=Fault;releaseNote();Serial.println("PAD_RGB_FAULT verify model, bank and BLE");}
    void request(uint8_t cmd,const uint8_t*p,size_t n,Phase next){
        phase=next;deadline=millis()+3500;if(!sendConfig(cmd,p,n))fail();
    }
    static uint32_t rgb(const uint8_t*p){return uint32_t(p[0])<<16|uint32_t(p[1])<<8|p[2];}
    uint32_t target(unsigned i) const{
        if(held[i]||pulse[i])return 0xffffff;
        if(learning&&(padFpga.scoreGuide?padFpga.cue==(16+i):(step<sizeof(melody)&&i==melody[step])))return 0xffcf00;
        static constexpr uint32_t bankColors[]={
            0x993ac9,0x5942ba,0x164eb8,0x2058e8,0x2392b8,0xd46416,0xc44668,0xb21a35};
        int bank=(learning||padFpga.part<3)?0:padFpga.octave;
        return bankColors[bank<-3?0:bank>4?7:bank+3];
    }
    void transfer(bool write){
        unsigned addr=base+index*26+5;
        uint8_t data[]={5,uint8_t(addr),uint8_t(addr>>8),0,0,3,0,0,uint8_t(outgoing>>16),uint8_t(outgoing>>8),uint8_t(outgoing)};
        request(write?0x22:0x23,data,write?11:8,write?Ack:Verify);
    }
public:
    void readControls(){
        constexpr unsigned addr=4*2931-19;
        uint8_t data[]={5,uint8_t(addr),uint8_t(addr>>8),0,0,16,0,0};
        request(0x23,data,8,Controls);
    }
    void setup(){}
    bool receiving()const{return phase==Model||phase==Records||phase==Controls||phase==ControlsAck||phase==Ack||phase==Verify;}
    bool busy()const{return receiving()||wanted();}
    void disconnected(){phase=Offline;pitch=0;step=0;learning=pendingHit=false;clearPresses();}
    void clearPresses(){memset(held,0,sizeof(held));memset(pulse,0,sizeof(pulse));}
    void refresh(){if(!receiving())phase=Offline;}
    void tick(){
        if(pitch&&due(offAt))releaseNote();
        if(!client->isConnected()||!configNotify||phonePhase)return;
        if(receiving()){if(due(deadline))fail();return;}
        if(phase==Fault)return;
        if(phase==Offline){request(0x11,nullptr,0,Model);return;}
        if(learning!=wanted()){releaseNote();step=0;learning=wanted();pendingHit=false;clearPresses();}
        for(unsigned i=0;i<count;i++)if(pulse[i]&&shown[i]==0xffffff&&due(pulseUntil[i]))pulse[i]=false;
        if(pendingHit&&!pulse[melody[step]]){
            pendingHit=false;++step;if(step==sizeof(melody))Serial.println("LESSON_COMPLETE");
        }
        for(unsigned n=0;n<count;n++){
            unsigned i=(cursor+n)%count;
            if(shown[i]!=target(i)){
                index=i;cursor=(i+1)%count;outgoing=target(i);transfer(true);return;
            }
        }
    }
    bool receive(uint8_t cmd,const uint8_t*p,size_t n){
        if(!receiving())return false;
        if(phase==Model){
            const char model[]="SMC-PAD Pocket_004";
            if(cmd!=0x11||n<sizeof(model)-1||memcmp(p,model,sizeof(model)-1)||(n>=sizeof(model)&&p[sizeof(model)-1]))fail();
            else{uint8_t data[]={5,uint8_t(base),uint8_t(base>>8),0,0,0xa0,1,0};request(0x23,data,8,Records);}
        }else if(phase==Records){
            const uint8_t header[]={5,uint8_t(base),uint8_t(base>>8),0,0,0xa0,1,0};
            if(cmd!=0x23||n!=8+26*count||memcmp(p,header,8)){fail();return true;}
            for(unsigned i=0;i<count;i++){
                const uint8_t*r=p+8+26*i;
                if(r[0]!=0||r[1]>15||r[2]>127){fail();return true;}
                keys[i]=r[2];channels[i]=r[1];shown[i]=rgb(r+5);
            }
            readControls();
        }else if(phase==ControlsAck){
            if(cmd!=0||n!=1||p[0])fail();else readControls();
        }else if(phase==Controls){
            constexpr unsigned baseAddr=4*2931-19;
            const uint8_t header[]={5,uint8_t(baseAddr),uint8_t(baseAddr>>8),0,0,16,0,0};
            const uint8_t factory[]={0,0,0,0,0,0,0,0,5,4,7,6,1,8,3,2};
            if(cmd!=0x23||n!=24||memcmp(p,header,8)){fail();return true;}
            for(unsigned i=0;i<16;i++)if(p[8+i]&&p[8+i]!=factory[i]){fail();return true;}
            for(unsigned i=8;i<16;i+=4){
                if(!(p[8+i]|p[9+i]|p[10+i]|p[11+i]))continue;
                unsigned addr=baseAddr+i;
                uint8_t data[]={5,uint8_t(addr),uint8_t(addr>>8),0,0,4,0,0,0,0,0,0};
                request(0x22,data,sizeof(data),ControlsAck);return true;
            }
            phase=Ready;Serial.println("PAD_RGB_READY 16 note pads, control overrides cleared");
        }else if(phase==Ack){
            if(cmd!=0||n!=1||p[0])fail();else transfer(false);
        }else{
            unsigned addr=base+index*26+5;
            const uint8_t header[]={5,uint8_t(addr),uint8_t(addr>>8),0,0,3,0,0};
            if(cmd!=0x23||n!=11||memcmp(p,header,8)||rgb(p+8)!=outgoing)fail();
            else{shown[index]=outgoing;if(outgoing==0xffffff)pulseUntil[index]=millis()+110;phase=Ready;}
        }
        return true;
    }
    bool midi(uint8_t status,uint8_t key,uint8_t velocity){
        uint8_t kind=status&0xf0;
        if(status==255||(kind==176&&(key==120||key==123))){clearPresses();return false;}
        if(kind!=128&&kind!=144)return false;
        if(phase!=Ready&&phase!=Ack&&phase!=Verify)return wanted();
        bool on=kind==144&&velocity!=0;
        bool mapped=padFpga.online&&padFpga.configKnown&&padFpga.scorePlaying&&!wanted()&&padFpga.scoreIndex<5;
        bool matched=false;
        for(unsigned i=0;i<count;i++){
            if(keys[i]!=key||channels[i]!=(status&15))continue;
            matched=true;
            if(mapped&&(!on||!held[i])){
                const auto &chord=chordPads[padFpga.scoreIndex][padFpga.part][i];
                for(unsigned n=0;n<chord[0];++n)padFpga.midi((on?0x90:0x80)|i,chord[n+1],velocity,millis(),true);
            }
            if(!on){held[i]=false;continue;}
            if(held[i])continue;
            held[i]=pulse[i]=true;pulseUntil[i]=millis()+110;
            if(learning&&wanted()&&padFpga.scoreGuide){
                if(padFpga.cue==16+i&&shown[i]==0xffcf00)
                    padFpga.event(22,i,60,velocity,0,padFpga.cueTag);
                continue;
            }
            if(!learning||!wanted()||pendingHit||step>=sizeof(melody)||melody[step]!=i||shown[i]!=0xffcf00||padFpga.owner!=2)continue;
            releaseNote();pitch=scale[i];padFpga.midi(0x99,pitch,96,millis());
            bool sent=false;for(auto &note:padFpga.notes)if(note.key==pitch&&note.sent)sent=true;
            if(sent){pendingHit=true;offAt=millis()+(step%7==6?900:420);}else releaseNote();
        }
        return wanted()||(mapped&&matched);
    }
};
constexpr uint8_t PadLesson::melody[];
constexpr uint8_t PadLesson::scale[];
PadLesson lesson;
