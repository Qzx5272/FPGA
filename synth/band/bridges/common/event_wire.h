#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
namespace starcluster {
constexpr size_t FRAME=34, GUARDED=98;
inline uint32_t crc32(const uint8_t* p,size_t n){
 uint32_t c=~0u;while(n--){c^=*p++;for(int k=0;k<8;k++)c=(c>>1)^(0xedb88320u&uint32_t(-int(c&1)));}return ~c;
}
inline uint32_t u32(const uint8_t*p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
inline void put32(uint8_t*p,uint32_t v){for(int i=0;i<4;i++)p[i]=v>>(i*8);}
inline void make(uint8_t*out,uint8_t kind,uint8_t source,uint8_t part=0,uint8_t contact=0,
 uint8_t note=60,uint8_t velocity=100,uint8_t flags=0,uint32_t epoch=0,uint32_t serial=0,uint32_t parameter=0){
 memset(out,0,GUARDED);out[0]=0xb4;out[1]=0x4b;out[2]=4;out[3]=kind;out[4]=source;out[5]=part;
 out[6]=contact;out[7]=note;out[8]=velocity;out[9]=flags;put32(out+10,epoch);put32(out+14,serial);
 put32(out+26,parameter);put32(out+30,crc32(out+2,28));
}
inline bool valid(const uint8_t*p){return p[0]==0xb4&&p[1]==0x4b&&p[2]==4&&u32(p+30)==crc32(p+2,28);}
// Sliding resynchronization survives partial writes, garbage and broken CRCs.
struct Parser {
 uint8_t data[FRAME];size_t used=0;uint32_t bad=0;
 bool feed(uint8_t b){
  if(used==FRAME)used=0;
  data[used++]=b;
  while(used&&data[0]!=0xb4){memmove(data,data+1,--used);}
  if(used>=2&&data[1]!=0x4b){memmove(data,data+1,--used);return false;}
  if(used!=FRAME)return false;
  if(valid(data))return true;
  ++bad;memmove(data,data+1,--used);return false;
 }
};
}
