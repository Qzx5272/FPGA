'use strict';
const $=id=>document.getElementById(id);
const service='4fafc201-1fb5-459e-8fcc-c5c9c331914b';
let device,rx,tx,timer,id=0,pending=null,ready=false,operating=false,watchdog;
const buttons=()=>document.querySelectorAll('.color').forEach(b=>b.disabled=!ready||!!pending||operating);
function reset(){clearInterval(timer);clearTimeout(watchdog);rx=tx=null;ready=false;pending=null;operating=false;buttons();$('connect').disabled=false;$('disconnect').disabled=true;$('connection').textContent='蓝牙已断开';$('pad').textContent='等待重新连接';$('result').textContent='连接已结束；重新连接后可读取上次结果';}
function receive(v){
 if(v.byteLength!==20||v.getUint8(0)!==0x53||v.getUint8(1)!==1)return;
 ready=!!v.getUint8(2)&&!!v.getUint8(3);$('pad').textContent=ready?'打击垫已连接，配置通道就绪':'正在寻找打击垫，请保持开机';
 const s=v.getUint8(9),a=v.getUint8(10),b=v.getUint8(11),kind=s&240;
 const name=kind===144&&b?'按下':kind===128||kind===144?'松开':kind===208?'通道压力':'MIDI';
 if(s)$('midi').textContent=`${name} · 通道 ${(s&15)+1} · 数据 ${a}, ${b}`;
 $('counts').textContent=`已解析 ${v.getUint32(12,true)} 条事件 · 队列丢包 ${v.getUint32(16,true)}`;
 const result=v.getUint8(5),reply=v.getUint8(4);
 if((pending===null||reply===pending)&&result){
  const labels={1:'处理中：核对型号、写入、回读…',2:'回读一致，改色已确认',3:'打击垫尚未就绪',4:'型号不匹配，未写入',5:'设备写入失败或拒绝',6:'回读或校验不一致',7:'超时或打击垫断开；结果未确认'};
  $('result').textContent=labels[result]||'未知状态';
  if(result===2)$('swatch').style.background=`rgb(${v.getUint8(6)},${v.getUint8(7)},${v.getUint8(8)})`;
  if(result!==1&&reply===pending){pending=null;clearTimeout(watchdog);}
 }
 buttons();
}
$('connect').onclick=async()=>{
 $('connect').disabled=true;
 try{
  if(!isSecureContext||!navigator.bluetooth)throw Error('需要安卓 Chrome 与 HTTPS / localhost 安全页面');
  device=await navigator.bluetooth.requestDevice({filters:[{services:[service]}]});device.addEventListener('gattserverdisconnected',reset);
  const g=await device.gatt.connect(),s=await g.getPrimaryService(service);
  rx=await s.getCharacteristic(service.replace('c201','c202'));tx=await s.getCharacteristic(service.replace('c201','c203'));
  tx.addEventListener('characteristicvaluechanged',e=>receive(e.target.value));await tx.startNotifications();
  const initial=await tx.readValue();if(initial.byteLength===20)id=initial.getUint8(4);receive(initial);$('connection').textContent='已连接 Starcluster-Control';$('disconnect').disabled=false;
  timer=setInterval(async()=>{if(operating||!tx)return;operating=true;try{receive(await tx.readValue());}catch(e){$('connection').textContent=e.message;}finally{operating=false;buttons();}},1000);
 }catch(e){if(device?.gatt.connected)device.gatt.disconnect();reset();$('connection').textContent=e.message;}
};
$('disconnect').onclick=()=>{device?.gatt.disconnect();reset();};
async function color(rgb){
 if(!ready||pending!==null||operating||!rx)return;
 id=(id+1)&255;pending=id;operating=true;buttons();$('result').textContent='正在发送…';
 const p=new Uint8Array([0x53,1,id,1,...rgb,0]);p[7]=(~p.slice(0,7).reduce((a,b)=>a+b,0))&255;
 watchdog=setTimeout(()=>{pending=null;$('result').textContent='未收到确认，请检查连接；不会自动重发';buttons();},15000);
 try{await rx.writeValueWithResponse(p);}catch(e){clearTimeout(watchdog);pending=null;$('result').textContent=`发送失败：${e.message}`;}finally{operating=false;buttons();}
}
document.querySelectorAll('[data-rgb]').forEach(b=>b.onclick=()=>color(b.dataset.rgb.split(',').map(Number)));
$('apply').onclick=()=>color($('custom').value.slice(1).match(/../g).map(x=>parseInt(x,16)));
