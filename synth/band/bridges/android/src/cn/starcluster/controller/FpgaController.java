package cn.starcluster.controller;
import android.os.*;import java.util.*;
final class FpgaController {
 interface Listener {void changed();void message(String text);}
 final BleLink ble;final Listener listener;final Handler ui=new Handler(Looper.getMainLooper());
 boolean running=false,identity=false,playing=false;int part=6,owner=0,active=0;long epoch=0,build=0,features=0,lastReply=0,lastIdentity=0,serial=1;
 static final String[] TITLES={"小星星","欢乐颂","星群·合流","四类乐器示范","音阶与和弦练习"};
 static final String[] VOICES={"底鼓","军鼓","踩镲","贝斯","电钢琴","簧管","主奏","合唱","拨弦","笛","钟","木琴","弓弦","管风琴","铜管","电子歌手"};
 static final int[] MASKS={0x18,0x18,0xff,0x5f81,0x3300};
 int boardSong=-1,boardPart=-1,cue=-1,mode=0,beat=0;
 boolean configured=false;
 byte[] buffer=new byte[34];int used=0;long badCrc=0;
 String state="等待 FPGA 身份";
 static final class Note {int note,velocity,part;long serial,epoch,at;boolean sent;}
 final HashMap<Integer,Note> notes=new HashMap<>();
 FpgaController(BleLink b,Listener l){ble=b;listener=l;}
 final Runnable heartbeat=new Runnable(){public void run(){if(!running)return;long now=SystemClock.elapsedRealtime();
  if(ble.linked&&ble.fpgaRx!=null){send(6,part,0,60,100,0,0,0,0);if(now-lastIdentity>2000){send(18,part,0,60,100,0,0,0,0);lastIdentity=now;}else if(identity&&build>=0x20261107L)send(20,part,0,60,100,0,0,0,0);}
  if(identity&&now-lastReply>2000){identity=false;owner=0;notes.clear();state="FPGA 应答超时，演奏已锁定";listener.changed();}
  for(Integer key:new ArrayList<>(notes.keySet())){Note n=notes.get(key);if(!n.sent&&now-n.at>1500){notes.remove(key);listener.message("声部授权超时，音符未发送");}}
  ui.postDelayed(this,250);
 }};
 void start(){if(running)return;running=true;ui.post(heartbeat);}
 void pause(){release();running=false;ui.removeCallbacks(heartbeat);}
 void disconnected(){identity=false;configured=false;boardSong=-1;boardPart=-1;cue=-1;owner=0;used=0;notes.clear();state="等待 FPGA 身份";listener.changed();}
 boolean ready(){return identity&&ble.linked&&SystemClock.elapsedRealtime()-lastReply<=2000;}
 void send(int k,int p,int c,int n,int v,int f,long e,long s,int value){ble.writeFpga(FpgaWire.frame(k,p,c,n,v,f,e,s,value));}
 void receive(byte[] data){for(byte b:data){if(used==34)used=0;buffer[used++]=b;while(used>0&&(buffer[0]&255)!=180)shift();if(used>=2&&buffer[1]!=75){shift();continue;}if(used<34)continue;if(!FpgaWire.valid(buffer)){badCrc++;shift();continue;}handle(buffer.clone());used=0;}}
 void shift(){System.arraycopy(buffer,1,buffer,0,--used);}
 void handle(byte[] p){lastReply=SystemClock.elapsedRealtime();int kind=p[3]&255;
  if(kind==161){build=FpgaWire.u32(p,6);features=FpgaWire.u32(p,22);identity=(features&4096)!=0;state=identity?"FPGA 在线 · 构建 "+Long.toHexString(build).toUpperCase():"固件未声明独立手机串口";}
  if(kind==163&&build>=0x20261107L&&(p[11]&255)==0xb5){
   int flags=p[15]&255;boardSong=flags&7;boardPart=p[4]&15;playing=(flags&8)!=0;
   mode=p[7]==3?3:(flags&32)!=0?4:(flags&16)!=0?2:1;
   cue=(p[12]&16)!=0?(p[12]&15)+1:-1;configured=true;
  }
  if((kind==128||kind==129)&&(p[5]&255)==part){owner=p[4]&255;epoch=FpgaWire.u32(p,10);active=(p[6]&255)|((p[7]&255)<<8);playing=kind==129;
   if(ready()&&owner==3)for(Integer key:new ArrayList<>(notes.keySet())){Note n=notes.get(key);if(!n.sent&&n.part==part){n.epoch=epoch;n.sent=true;send(0,n.part,key,n.note,n.velocity,0,n.epoch,n.serial,0);}}
  }listener.changed();
 }
 void rehearsal(int song,int target,int action){
  if(!ready()||build<0x20261107L){listener.message("需要连接新版 FPGA 和 C3");return;}
  if(song<0||song>=TITLES.length||target<0||target>=16||(MASKS[song]&(1<<target))==0||action<0||action>4){listener.message("此曲没有所选声部");return;}
  release();send(23,target,0,60,100,action,0,0,song);
 }
 void select(int value){release();part=value;owner=0;epoch=0;if(ready())send(6,part,0,60,100,0,0,0,0);listener.changed();}
 void down(int key,int note,int velocity){if(!ready()){listener.message("等待真实 FPGA 身份后才能演奏");return;}if(notes.containsKey(key))return;Note n=new Note();n.note=note;n.velocity=velocity;n.part=part;n.serial=serial++;n.at=SystemClock.elapsedRealtime();notes.put(key,n);send(4,part,0,60,100,0,0,0,0);}
 void up(int key){Note n=notes.remove(key);if(n!=null&&n.sent)send(1,n.part,key,n.note,0,0,n.epoch,n.serial,0);}
 void release(){notes.clear();if(ble.linked)send(2,part,0,60,0,0,0,0,0);}
 void claim(){if(!ready()){listener.message("FPGA 未就绪");return;}send(4,part,0,60,100,0,0,0,0);}
 void transport(boolean stop){if(!ready()){listener.message("FPGA 未就绪");return;}if(stop)release();send(5,part,0,60,100,stop?1:0,0,0,0);}
 void parameter(int flag,int value){if(!ready()||owner!=3){listener.message("请先申请当前声部，等待授权为手机");return;}send(11,part,0,60,100,flag,epoch,0,value);}
}
