package cn.starcluster.controller;
import java.util.*;import android.os.SystemClock;
public class FpgaControllerTest {
 static byte[] reply(int kind,int owner,long epoch){byte[] p=FpgaWire.frame(kind,6,0,60,0,0,epoch,0,0);p[4]=(byte)owner;if(kind==161){FpgaWire.put(p,6,0x20261031);FpgaWire.put(p,22,4096);}FpgaWire.put(p,30,FpgaWire.crc(p));return p;}
 static void check(boolean yes,String why){if(!yes)throw new AssertionError(why);}
 public static void main(String[] args){BleLink link=new BleLink();FpgaController c=new FpgaController(link,new FpgaController.Listener(){public void changed(){}public void message(String s){}});
  c.down(0,60,100);check(link.sent.isEmpty(),"identity gate");byte[] id=reply(161,0,0);c.receive(Arrays.copyOfRange(id,0,20));check(!c.identity,"partial identity");c.receive(Arrays.copyOfRange(id,20,34));check(c.ready(),"fragment reassembly");
  c.down(0,60,100);check(link.sent.get(0)[3]==4,"claim first");c.up(0);c.receive(reply(128,3,7));check(link.sent.size()==1,"release before claim must cancel note");
  c.down(1,64,90);c.receive(reply(128,2,8));check(link.sent.size()==2,"other owner must not start note");c.receive(reply(128,3,9));byte[] on=link.sent.get(2);check(on[3]==0&&FpgaWire.u32(on,10)==9,"accepted epoch note on");
  c.receive(reply(128,3,10));c.up(1);byte[] off=link.sent.get(3);check(off[3]==1&&FpgaWire.u32(off,10)==9&&FpgaWire.u32(off,14)==FpgaWire.u32(on,14),"off must retain original epoch and serial");
  c.down(2,67,100);c.pause();check(link.sent.get(link.sent.size()-1)[3]==2&&c.notes.isEmpty(),"background release");
  c.running=true;SystemClock.now=5000;c.heartbeat.run();check(!c.identity,"stale identity expiration");int count=link.sent.size();c.down(3,72,100);check(link.sent.size()==count,"no note after timeout");
  System.out.println("PASS: identity gate, BLE fragments, release-before-grant, ownership, original note-off identity, background release, timeout");
 }
}
