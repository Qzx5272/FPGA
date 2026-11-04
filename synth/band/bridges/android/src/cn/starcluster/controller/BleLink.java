package cn.starcluster.controller;
import android.app.*;import android.bluetooth.*;import android.bluetooth.le.*;import android.os.*;
import java.util.*;

final class BleLink {
 static final UUID SERVICE=UUID.fromString("4fafc201-1fb5-459e-8fcc-c5c9c331914b");
 static UUID uuid(int n){return UUID.fromString("4fafc20"+n+"-1fb5-459e-8fcc-c5c9c331914b");}
 static final UUID CCC=UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
 interface Listener {void state(String text,boolean ready);void status(byte[] p);void midi(byte[] p);void fpga(byte[] p);void device(BluetoothDevice d,String name);}
 final Activity activity;final Listener listener;final Handler main=new Handler(Looper.getMainLooper());
 BluetoothGatt gatt;BluetoothLeScanner scanner;BluetoothGattCharacteristic rx,status,events,fpgaRx,fpgaTx;
 boolean linked=false,busy=false,scanning=false;int generation=0;
 final ArrayDeque<Runnable> queue=new ArrayDeque<>();
 final HashSet<String> seen=new HashSet<>();
 final Runnable timeout=()->fail("蓝牙操作超时，请重新连接");
 BleLink(Activity a,Listener l){activity=a;listener=l;}
 void scan(){close();BluetoothAdapter adapter=((BluetoothManager)activity.getSystemService(Activity.BLUETOOTH_SERVICE)).getAdapter();
  if(adapter==null||!adapter.isEnabled()){listener.state("请先开启手机蓝牙",false);return;}
  scanner=adapter.getBluetoothLeScanner();seen.clear();scanning=true;
  scanner.startScan(Arrays.asList(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(SERVICE)).build()),new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),scanCallback);
  listener.state("正在扫描 C3…",false);int token=generation;main.postDelayed(()->{if(token==generation&&scanning){stopScan();listener.state(seen.isEmpty()?"未找到 C3，请确认供电与固件":"请选择下方设备",false);}},12000);
 }
 final ScanCallback scanCallback=new ScanCallback(){public void onScanResult(int type,ScanResult r){main.post(()->{if(scanning&&seen.add(r.getDevice().getAddress()))listener.device(r.getDevice(),r.getScanRecord()!=null?r.getScanRecord().getDeviceName():"C3");});}
  public void onScanFailed(int code){main.post(()->{scanning=false;listener.state("扫描失败："+code,false);});}};
 void stopScan(){if(scanner!=null&&scanning)scanner.stopScan(scanCallback);scanning=false;}
 void connect(BluetoothDevice d){close();listener.state("正在连接 C3…",false);gatt=d.connectGatt(activity,false,callback,BluetoothDevice.TRANSPORT_LE);main.postDelayed(timeout,12000);}
 void close(){generation++;stopScan();main.removeCallbacks(timeout);queue.clear();busy=false;linked=false;rx=status=events=fpgaRx=fpgaTx=null;
  if(gatt!=null){BluetoothGatt old=gatt;gatt=null;old.disconnect();old.close();}}
 void fail(String text){close();listener.state(text,false);}
 void enqueue(Runnable r){if(queue.size()>=96){fail("发送队列过载，已断开以释放音符");return;}queue.add(r);pump();}
 void pump(){if(busy||gatt==null||queue.isEmpty())return;busy=true;main.postDelayed(timeout,6000);queue.remove().run();}
 void done(int result){main.removeCallbacks(timeout);busy=false;if(result!=BluetoothGatt.GATT_SUCCESS){fail("蓝牙通信失败："+result);return;}pump();}
 void subscribe(BluetoothGattCharacteristic c){enqueue(()->{BluetoothGattDescriptor d=c.getDescriptor(CCC);if(d==null||!gatt.setCharacteristicNotification(c,true)){fail("通知服务不可用");return;}d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);if(!gatt.writeDescriptor(d))fail("无法订阅通知");});}
 void write(byte[] p){if(!linked||rx==null){listener.state("请先连接设备",false);return;}enqueue(()->{rx.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT);rx.setValue(p);if(!gatt.writeCharacteristic(rx))fail("命令未发送");});}
 void writeFpga(byte[] p){if(!linked||fpgaRx==null)return;for(int offset=0;offset<p.length;offset+=20){final byte[] chunk=Arrays.copyOfRange(p,offset,Math.min(offset+20,p.length));enqueue(()->{fpgaRx.setWriteType(BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT);fpgaRx.setValue(chunk);if(!gatt.writeCharacteristic(fpgaRx))fail("FPGA 命令未发送");});}}
 final BluetoothGattCallback callback=new BluetoothGattCallback(){
  public void onConnectionStateChange(BluetoothGatt g,int code,int state){main.post(()->{if(g!=gatt)return;if(code!=0||state==BluetoothProfile.STATE_DISCONNECTED){fail("蓝牙已断开（"+code+"）");return;}if(state==BluetoothProfile.STATE_CONNECTED){main.removeCallbacks(timeout);main.postDelayed(timeout,12000);if(!g.discoverServices())fail("无法查询服务");}});}
  public void onServicesDiscovered(BluetoothGatt g,int code){main.post(()->{if(g!=gatt)return;main.removeCallbacks(timeout);BluetoothGattService s=g.getService(SERVICE);if(code!=0||s==null){fail("不是兼容的星群控制服务");return;}rx=s.getCharacteristic(uuid(2));status=s.getCharacteristic(uuid(3));events=s.getCharacteristic(uuid(4));fpgaRx=s.getCharacteristic(uuid(5));fpgaTx=s.getCharacteristic(uuid(6));if(rx==null||status==null){fail("设备服务不完整");return;}subscribe(status);if(events!=null)subscribe(events);if(fpgaTx!=null)subscribe(fpgaTx);enqueue(()->{if(!g.readCharacteristic(status))fail("无法读取状态");});});}
  public void onDescriptorWrite(BluetoothGatt g,BluetoothGattDescriptor d,int code){main.post(()->{if(g==gatt)done(code);});}
  public void onCharacteristicWrite(BluetoothGatt g,BluetoothGattCharacteristic c,int code){main.post(()->{if(g==gatt)done(code);});}
  public void onCharacteristicRead(BluetoothGatt g,BluetoothGattCharacteristic c,int code){byte[] value=c.getValue()==null?new byte[0]:c.getValue().clone();main.post(()->{if(g!=gatt)return;if(code==0){linked=true;listener.state(events==null?"已连接 · 旧固件无事件回传":"已连接 · C3 蓝牙直连",true);listener.status(value);}done(code);});}
  public void onCharacteristicChanged(BluetoothGatt g,BluetoothGattCharacteristic c){byte[] value=c.getValue().clone();UUID id=c.getUuid();main.post(()->{if(g!=gatt)return;if(id.equals(uuid(3)))listener.status(value);else if(id.equals(uuid(4)))listener.midi(value);else if(id.equals(uuid(6)))listener.fpga(value);});}
 };
}
