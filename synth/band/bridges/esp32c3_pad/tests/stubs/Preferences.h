#pragma once
#include <vector>
#include <cstring>
struct Preferences {
 static std::vector<unsigned char> memory;
 bool begin(const char*,bool){return true;}
 size_t getBytesLength(const char*){return memory.size();}
 size_t getBytes(const char*,void* dst,size_t n){memcpy(dst,memory.data(),n);return n;}
 size_t putBytes(const char*,const void* src,size_t n){const auto* p=(const unsigned char*)src;memory.assign(p,p+n);return n;}
 bool remove(const char*){memory.clear();return true;}
};
