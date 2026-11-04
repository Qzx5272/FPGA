'use strict';
const $=id=>document.getElementById(id),service='6e400001-b5a3-f393-e0a9-e50e24dcca9e';
const names=['底鼓','军鼓','踩镲','贝斯','电钢琴','簧管','主奏','合唱 A/E/I/O/U','拨弦','笛','钟','木琴','弓弦','管风琴','铜管','电子歌手（需麦克风）'];
names.forEach((name,i)=>$('part').add(new Option(name,i)));$('part').value=6;
let device,rx,tx,identity=false,features=0,serial=1,buffer=[],states=new Map(),held=new Map(),queue=[],busy=false,timer,recording=false,actions=[],recordStart=0;
const status=s=>$('status').textContent=s;
function crc32(a){let c=0xffffffff;for(const b of a){c^=b;for(let i=0;i<8;i++)c=(c>>>1)^((c&1)?0xedb88320:0);}return(c^0xffffffff)>>>0;}
function frame(kind,part=+$('part').value,contact=0,note=60,velocity=100,flags=0,epoch=0,seq=0,parameter=0){
 const a=new Uint8Array(34),v=new DataView(a.buffer);a.set([0xb4,0x4b,4,kind,3,part,contact,note,velocity,flags]);v.setUint32(10,epoch,true);v.setUint32(14,seq,true);v.setUint32(26,parameter,true);v.setUint32(30,crc32(a.slice(2,30)),true);return a;
}
function send(a){
 if(!rx)return Promise.reject(Error('未连接'));
 if(queue.length>96){queue=[];held.clear();queue.push({a:frame(2),resolve:()=>{},reject:()=>{}});status('发送过载，已停止手机音符');return Promise.reject(Error('过载'));}
 return new Promise((resolve,reject)=>{queue.push({a,resolve,reject});pump();});
}
async function pump(){if(busy)return;busy=true;while(queue.length&&rx){const item=queue.shift();try{for(let i=0;i<34;i+=20)await rx.writeValueWithResponse(item.a.slice(i,i+20));item.resolve();}catch(e){item.reject(e);disconnect();break;}}busy=false;}
function receive(e){buffer.push(...new Uint8Array(e.target.value.buffer,e.target.value.byteOffset,e.target.value.byteLength));
 while(buffer.length>=34){if(buffer[0]!==0xb4||buffer[1]!==0x4b){buffer.shift();continue;}const a=Uint8Array.from(buffer.slice(0,34)),v=new DataView(a.buffer);if(crc32(a.slice(2,30))!==v.getUint32(30,true)){buffer.shift();continue;}buffer.splice(0,34);
  if(a[3]===0xa1){identity=true;features=v.getUint32(22,true);status('已连接 FPGA，构建 '+v.getUint32(6,true)+'；演奏席3');}
  else if([128,129,144,145].includes(a[3]))states.set(a[5],{owner:a[4],epoch:v.getUint32(10,true),at:performance.now()});
 }
}
function action(data){if(recording)actions.push({at_ms:Math.round(performance.now()-recordStart),...data});}
async function padDown(index){
 if(!rx||!identity){status('请先连接并等待 FPGA 身份');return;}
 const part=+$('part').value;if(part>=8&&part<=14&&!(features&64)){status('该固件没有扩展音色');return;}
 if(held.has(index))return;
 const h={part,note:60+[0,2,4,5,7,9,11,12,14,16,17,19,21,23,24,26][index],velocity:+$('velocity').value,serial:serial++,sent:false};held.set(index,h);
 try{
  await send(frame(4,part));const start=performance.now();
  while(held.get(index)===h){const s=states.get(part);if(s&&s.at>=start-50&&s.owner===3){h.epoch=s.epoch;break;}if(performance.now()-start>2000)throw Error('声部授权超时或被其他席位占用');await new Promise(r=>setTimeout(r,20));}
  if(held.get(index)!==h)return;
  h.sent=true;await send(frame(0,part,index,h.note,h.velocity,0,h.epoch,h.serial));action({kind:'on',...h,index});
 }catch(e){held.delete(index);status(e.message);}
}
async function padUp(index){const h=held.get(index);if(!h)return;held.delete(index);if(h.sent)try{await send(frame(1,h.part,index,h.note,0,0,h.epoch,h.serial));action({kind:'off',index});}catch{} }
async function allOff(){held.clear();document.querySelectorAll('.on').forEach(b=>b.classList.remove('on'));if(rx)try{await send(frame(2));}catch{}action({kind:'release_source'});}
function disconnect(){clearInterval(timer);rx=null;tx=null;identity=false;held.clear();states.clear();buffer=[];while(queue.length)queue.shift().reject(Error('断开连接'));status('蓝牙已断开；FPGA 席位租约会释放音符');}
$('connect').onclick=async()=>{try{
 if(!navigator.bluetooth)throw Error('浏览器不支持 Web Bluetooth');
 if(device?.gatt.connected){await allOff();device.gatt.disconnect();}
 device=await navigator.bluetooth.requestDevice({filters:[{services:[service]}]});device.addEventListener('gattserverdisconnected',disconnect);
 const server=await device.gatt.connect(),s=await server.getPrimaryService(service);rx=await s.getCharacteristic(service.replace('0001','0002'));tx=await s.getCharacteristic(service.replace('0001','0003'));await tx.startNotifications();tx.addEventListener('characteristicvaluechanged',receive);
 await send(frame(18));timer=setInterval(()=>{if(rx)send(frame(6)).catch(()=>{});if(!identity&&rx)send(frame(18)).catch(()=>{});},250);status('蓝牙已连接，等待 FPGA 身份…');
}catch(e){status(e.message);}};
for(let i=0;i<16;i++){const b=document.createElement('button');b.textContent=String(i+1).padStart(2,'0');b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);b.classList.add('on');padDown(i);};b.onpointerup=b.onpointercancel=b.onlostpointercapture=()=>{b.classList.remove('on');padUp(i);};$('pads').append(b);}
function control(flag,value){const part=flag===2?7:+$('part').value,s=states.get(part);if(!s||s.owner!==3){status('先按该声部打击垫取得控制权');return;}send(frame(11,part,0,60,100,flag,s.epoch,0,value)).catch(e=>status(e.message));action({kind:'parameter',part,flag,value});}
for(const [id,flag] of [['expression',0],['bend',1]]){let pending;$(id).oninput=()=>{clearTimeout(pending);pending=setTimeout(()=>control(flag,+$(id).value),35);};}
$('vowel').onchange=()=>control(2,$('vowel').selectedIndex);
$('part').onchange=allOff;$('stop').onclick=allOff;
async function transport(flags){if(!identity){status('请先连接 FPGA 并核对板端身份');return;}try{await send(frame(5,+$('part').value,0,60,100,flags));action({kind:'transport',flags});status(flags?'已发送停止演出':'已发送开始板载曲目');}catch(e){status(e.message);}}
$('playSong').onclick=()=>transport(0);
$('stopSong').onclick=async()=>{await allOff();await transport(1);};
 $('record').onclick=()=>{recording=!recording;if(recording){actions=[];recordStart=performance.now();for(const [index,h] of held)if(h.sent)actions.push({at_ms:0,kind:'on',...h,index});}else{const at_ms=Math.round(performance.now()-recordStart);for(const index of held.keys())actions.push({at_ms,kind:'off',index});} $('record').textContent=recording?'结束记录':'开始记录手机动作';};
$('save').onclick=()=>{
 const events=[],live=new Map();let duration=0;
 const event=(kind,part=6,contact=0,note=60,velocity=100,flags=0,epoch=0,serial=0,parameter=0)=>({kind,source:3,part,contact,note,velocity,flags,epoch,serial,sample:0,parameter});
 for(const a of actions){const at_us=a.at_ms*1000;duration=Math.max(duration,at_us);let e;
  if(a.kind==='on'){e=event(0,a.part,a.index,a.note,a.velocity,0,a.epoch,a.serial);live.set(a.index,e);}
  else if(a.kind==='off'&&live.has(a.index)){e={...live.get(a.index),kind:1,velocity:0};live.delete(a.index);}
  else if(a.kind==='parameter')e=event(11,a.part,0,60,100,a.flag,0,0,a.value);
  else if(a.kind==='transport')e=event(5,6,0,60,100,a.flags);
  else if(a.kind==='release_source'){for(const n of live.values())events.push({at_us,event:{...n,kind:1,velocity:0}});live.clear();}
  if(e)events.push({at_us,event:e});
 }
 for(const n of live.values())events.push({at_us:duration,event:{...n,kind:1,velocity:0}});
 const take={format:'starcluster-take-1',duration_us:duration,performance:{},events,origin:'phone-seat3'};
 const url=URL.createObjectURL(new Blob([JSON.stringify(take,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='phone.take.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
document.addEventListener('visibilitychange',()=>{if(document.hidden)allOff();});window.addEventListener('pagehide',allOff);
