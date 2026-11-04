package cn.starcluster.controller;
import java.util.zip.CRC32;
final class FpgaWire {
 static long u32(byte[] p,int i){return (p[i]&255L)|((p[i+1]&255L)<<8)|((p[i+2]&255L)<<16)|((p[i+3]&255L)<<24);}
 static void put(byte[] p,int i,long n){for(int k=0;k<4;k++)p[i+k]=(byte)(n>>(8*k));}
 static long crc(byte[] p){CRC32 c=new CRC32();c.update(p,2,28);return c.getValue();}
 static boolean valid(byte[] p){return p.length==34&&(p[0]&255)==180&&p[1]==75&&p[2]==4&&u32(p,30)==crc(p);}
 static byte[] frame(int kind,int part,int contact,int note,int velocity,int flag,long epoch,long serial,int value){
  byte[] p=new byte[34];p[0]=(byte)180;p[1]=75;p[2]=4;p[3]=(byte)kind;p[4]=3;p[5]=(byte)part;p[6]=(byte)contact;p[7]=(byte)note;p[8]=(byte)velocity;p[9]=(byte)flag;put(p,10,epoch);put(p,14,serial);put(p,26,value);put(p,30,crc(p));return p;
 }
}
