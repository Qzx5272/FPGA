'use strict';
// Run the actual phone controller with a small DOM and GATT transport mock.
// This verifies the event flow, not browser pairing or a radio connection.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const elements=new Map(),writes=[];let download;
function element(){return {value:'0',selectedIndex:0,textContent:'',children:[],
 classList:{add(){},remove(){}},add(o){this.children.push(o);},append(o){this.children.push(o);},
 setPointerCapture(){},click(){}};}
function get(id){if(!elements.has(id))elements.set(id,element());return elements.get(id);}
get('velocity').value='96';get('expression').value='110';get('bend').value='8192';
const context=vm.createContext({Uint8Array,DataView,Map,Promise,Math,Error,Blob,performance,
 setTimeout,clearTimeout,setInterval,clearInterval,Option:function(label,value){return {label,value};},
 document:{getElementById:get,createElement:element,querySelectorAll:()=>[],addEventListener(){}},
 window:{addEventListener(){}},navigator:{},
 URL:{createObjectURL(b){download=b;return 'blob:test';},revokeObjectURL(){}},
 mockRx:{async writeValueWithResponse(a){writes.push(Uint8Array.from(a));}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../bridges/phone/controller.js'),'utf8'),context);
(async()=>{
 assert.equal(get('pads').children.length,16);
 await vm.runInContext('transport(0)',context);assert.equal(writes.length,0);
 vm.runInContext('rx=mockRx;const id=frame(161);new DataView(id.buffer).setUint32(22,0x8000007c,true);new DataView(id.buffer).setUint32(30,crc32(id.slice(2,30)),true);receive({target:{value:new DataView(id.buffer)}});',context);
 assert.equal(vm.runInContext('features',context),0x8000007c);
 vm.runInContext('states.set(6,{owner:3,epoch:8,at:performance.now()});',context);
 get('record').onclick();await get('playSong').onclick();
 await vm.runInContext('padDown(0)',context);await vm.runInContext('padUp(0)',context);
 vm.runInContext('control(0,90)',context);await new Promise(r=>setTimeout(r,10));
 await get('stopSong').onclick();get('record').onclick();get('save').onclick();
 const take=JSON.parse(await download.text());
 assert.equal(take.format,'starcluster-take-1');
 assert.deepEqual(take.events.map(x=>x.event.kind),[5,0,1,11,5]);
 assert.deepEqual(take.events.filter(x=>x.event.kind===5).map(x=>x.event.flags),[0,1]);
 assert.equal(take.events.find(x=>x.event.kind===0).event.velocity,96);
 const all=Buffer.concat(writes.map(x=>Buffer.from(x)));assert.equal(all.length%34,0);
 for(let i=0;i<all.length;i+=34){
  assert.equal(all[i],0xb4);assert.equal(all[i+1],0x4b);
  context.checkFrame=Uint8Array.from(all.subarray(i,i+34));
  assert(vm.runInContext('crc32(checkFrame.slice(2,30))===new DataView(checkFrame.buffer).getUint32(30,true)',context));
 }
 console.log(JSON.stringify({status:'passed',pads:16,frames:all.length/34,recorded_kinds:take.events.map(x=>x.event.kind),
  scope:'Actual phone controller: identity offset,20-byte GATT fragments,ownership,notes,controls,transport and export;no radio or pairing verification'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
