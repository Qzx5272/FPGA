#include "../src/midi_packet.h"
#include <vector>
#include <array>
#include <cassert>
#include <iostream>
using Message=std::array<unsigned,4>;
std::vector<Message> parse(std::initializer_list<uint8_t> bytes,bool expected=true) {
    std::vector<uint8_t> p(bytes);std::vector<Message> result;
    bool ok=decodeMidiPacket(p.data(),p.size(),[&](uint8_t s,uint8_t a,uint8_t b,uint16_t ts){result.push_back({s,a,b,ts});});
    assert(ok==expected);return result;
}
int main() {
    assert((parse({0x80,0x80,0x99,36,100})==std::vector<Message>{{0x99,36,100,0}}));
    assert((parse({0x81,0xff,0x89,36,0})==std::vector<Message>{{0x89,36,0,255}}));
    auto p=parse({0x80,0x81,0x99,36,100,0x82,0x99,36,0});
    assert(p.size()==2 && p[1][2]==0 && p[1][3]==2);
    p=parse({0x80,0x80,0x99,36,100,37,90,0x81,38,80});
    assert(p.size()==3 && p[2][1]==38);
    p=parse({0x80,0x80,0xc0,12,0x81,0xd0,90,0x82,0xa0,36,70,0x83,0xe0,0,64});
    assert(p.size()==4 && p[2][0]==0xa0);
    p=parse({0x80,0x80,0xf8,0x81,0x90,60,100});assert(p.size()==2);
    parse({},false);parse({0x80},false);parse({0,0x80,0x90,60,1},false);
    parse({0x80,0x80,60,100},false); // no running status across packets
    parse({0x80,0x80,0x90,60},false);
    parse({0x80,0x80,0x90,60,0x80},false);
    parse({0x80,0x80,0xf0,1,2,0xf7},false); // explicitly outside diagnostic scope
    parse({0x80,0x80,0x90,60,1,0x81},false);
    std::cout<<"PASS: note on/off, zero velocity, channels, timestamps, running status, pressure, CC-family lengths, realtime, malformed rejection\n";
}
