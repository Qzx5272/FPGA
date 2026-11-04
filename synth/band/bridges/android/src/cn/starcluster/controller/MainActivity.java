package cn.starcluster.controller;
import android.Manifest;import android.app.*;import android.bluetooth.*;import android.content.*;import android.content.pm.PackageManager;import android.graphics.Color;import android.graphics.Typeface;import android.graphics.drawable.GradientDrawable;import android.net.Uri;import android.os.*;import android.view.*;import android.widget.*;
import org.json.*;import java.io.*;import java.net.*;import java.nio.charset.StandardCharsets;import java.util.*;

public class MainActivity extends Activity implements BleLink.Listener {
 FpgaController synth;TextView fpgaState;int velocity=100;
 final int BG=0xfffaf5e9,CARD=0xfff1e8d8,INK=0xff292722,MUTED=0xff70665b,ACCENT=0xffa33727,GREEN=0xff276356;
 LinearLayout root,content,devices;TextView connection,padState,result,activityText,recordState;Button recordButton;
 BleLink ble;Handler ui=new Handler(Looper.getMainLooper());String page="设备",linkText="尚未连接",padText="等待打击垫",resultText="选择颜色，修改此前验证的那个垫",midiText="等待敲击";
 boolean ready=false,recording=false,incomplete=false;int requestId=0,pending=-1;String operation="";long decoded=0,dropped=0,lastSeq=-1,recordStart=0,recordDropped=0,recordFirst=-1,recordLast=-1;
 JSONArray recorded=new JSONArray();JSONObject lastTake=null,score=null;int[] notes=new int[16];int selected=0,profile=3,bank=1;Button[] keyButtons=new Button[16];EditText noteInput;Spinner profileSpinner,bankSpinner;
 final HashSet<Integer> live=new HashSet<>();String exportText="";int requests=0;
 final Runnable commandTimeout=()->{pending=-1;resultText="未收到设备确认，未自动重试";if(result!=null)result.setText(resultText);};
 @Override public void onCreate(Bundle state){super.onCreate(state);ble=new BleLink(this,this);synth=new FpgaController(ble,new FpgaController.Listener(){public void changed(){updateFpga();}public void message(String s){toast(s);}});for(int i=0;i<16;i++)notes[i]=getPreferences(0).getInt("note"+i,36+i);try{String s=readLocal("score.json");if(s!=null)score=validateScore(s);}catch(Exception ignored){}render();}
 int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
 TextView text(String s,int size,int color){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);t.setPadding(0,dp(5),0,dp(5));return t;}
 GradientDrawable background(int color,int radius){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));return d;}
 Button button(String name,Runnable action){Button b=new Button(this);b.setText(name);b.setAllCaps(false);b.setTextColor(BG);b.setTextSize(15);b.setBackground(background(ACCENT,12));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,dp(50));p.setMargins(0,dp(8),0,dp(5));b.setLayoutParams(p);b.setOnClickListener(v->action.run());return b;}
 LinearLayout card(String heading){LinearLayout c=new LinearLayout(this);c.setOrientation(1);c.setPadding(dp(18),dp(14),dp(18),dp(18));c.setBackground(background(CARD,18));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.setMargins(0,dp(14),0,0);content.addView(c,p);TextView h=text(heading,20,INK);h.setTypeface(null,Typeface.BOLD);c.addView(h);return c;}
 void render(){root=new LinearLayout(this);root.setOrientation(1);root.setBackgroundColor(BG);root.setPadding(dp(20),dp(14),dp(20),dp(10));setContentView(root);root.setOnApplyWindowInsetsListener((v,in)->{if(Build.VERSION.SDK_INT>=30){android.graphics.Insets x=in.getInsets(WindowInsets.Type.systemBars());root.setPadding(dp(20)+x.left,dp(14)+x.top,dp(20)+x.right,dp(10)+x.bottom);}return in;});root.requestApplyInsets();
  TextView title=text("星群合奏",26,INK);title.setTypeface(Typeface.SERIF,Typeface.BOLD);root.addView(title);root.addView(text("星群数字乐器 · 无线控制台",13,MUTED));
  LinearLayout nav=new LinearLayout(this);for(String name:new String[]{"设备","演奏","键位","曲谱","记录"}){Button b=button(name,()->{synth.release();page=name;render();});b.setPadding(0,0,0,0);b.setTextSize(14);b.setTextColor(page.equals(name)?BG:INK);b.setBackground(background(page.equals(name)?ACCENT:CARD,12));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(46),1);p.setMargins(dp(2),dp(8),dp(2),dp(4));nav.addView(b,p);}root.addView(nav);
  ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));content=new LinearLayout(this);content.setOrientation(1);scroll.addView(content);connection=padState=result=activityText=recordState=null;devices=null;recordButton=null;
  fpgaState=null;if(page.equals("设备"))devicePage();if(page.equals("演奏"))playPage();if(page.equals("键位"))keysPage();if(page.equals("曲谱"))scorePage();if(page.equals("记录"))recordPage();
 }
 final String[] padAudit=new String[16];
 int auditIndex=-1;
 boolean auditArmed=false;
 TextView auditView;
 void showAudit(){
  if(auditView==null)return;
  StringBuilder t=new StringBuilder();
  for(int i=0;i<16;i++)if(padAudit[i]!=null)t.append(i+1).append("号垫　").append(padAudit[i]).append("\n");
  if(auditIndex>=0&&auditIndex<16)t.append(auditArmed?"请敲 ":"点准备后再敲 ").append(auditIndex+1).append(" 号垫");
  else if(auditIndex==16)t.append("十六键检查结束");
  auditView.setText(t.toString());
 }
 void auditHit(int status,int key,int velocity){
  if(!auditArmed||auditIndex<0||auditIndex>=16)return;
  int kind=status&240;
  if(!(kind==144&&velocity>0)&&kind!=176&&kind!=192)return;
  String name=kind==144?"音符":kind==176?"控制器":"程序";
  String id=name+" "+key+"　通道 "+((status&15)+1);
  for(int i=0;i<auditIndex;i++)if(id.equals(padAudit[i])){id+="（与 "+(i+1)+" 号相同）";break;}
  padAudit[auditIndex++]=id;auditArmed=false;showAudit();
 }
 void auditCard(){
  LinearLayout c=card("十六键逐键检查");auditView=text("",14,INK);c.addView(auditView);
  c.addView(button("从一号垫重新检查",()->{Arrays.fill(padAudit,null);auditIndex=0;auditArmed=true;showAudit();}));
  c.addView(button("准备检查当前键",()->{if(auditIndex>=0&&auditIndex<16)auditArmed=true;showAudit();}));
  c.addView(button("当前键没有消息，跳过",()->{if(auditIndex>=0&&auditIndex<16){padAudit[auditIndex++]="未收到消息";auditArmed=false;}showAudit();}));
  showAudit();
 }
 void devicePage(){LinearLayout c=card("蓝牙连接");connection=text(linkText,17,GREEN);c.addView(connection);padState=text(padText,14,MUTED);c.addView(padState);c.addView(button("扫描并选择 C3",this::scan));c.addView(button("断开连接",()->{stopRecord("主动断开");ble.close();state("已断开",false);}));devices=new LinearLayout(this);devices.setOrientation(1);c.addView(devices);
  c=card("单垫色彩");c.addView(text("第 4 预设、键组 2 中此前验证的音符 24 垫。颜色按配置槽定位；更改键位后音符编号会变化。",14,MUTED));c.addView(button("朱红",()->color(250,0,0)));c.addView(button("靛蓝",()->color(0,0,250)));c.addView(button("薄荷绿",()->color(0,230,160)));result=text(resultText,14,GREEN);c.addView(result);
  c=card("实时活动");activityText=text(midiText,16,INK);c.addView(activityText);c.addView(text("音符由打击垫回传。进入演奏页可查看 FPGA 身份并使用手机触摸键演奏。",13,MUTED));
 }
 void scan(){if(recording){toast("请先结束记录");return;}if(Build.VERSION.SDK_INT>=31){if(checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)!=PackageManager.PERMISSION_GRANTED||checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT},10);return;}}else if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION},10);return;}
  if(devices!=null)devices.removeAllViews();try{ble.scan();}catch(SecurityException e){state("蓝牙权限未授予，请在系统设置中允许附近设备",false);} }
 @Override public void onRequestPermissionsResult(int r,String[] p,int[] grant){super.onRequestPermissionsResult(r,p,grant);if(r==10){boolean ok=grant.length>0;for(int g:grant)ok&=g==PackageManager.PERMISSION_GRANTED;if(ok)scan();else state("需要附近设备权限才能连接 C3",false);}}
 public void device(BluetoothDevice d,String name){if(devices!=null)devices.addView(button((name==null?"Starcluster-Control":name)+"\n"+d.getAddress(),()->ble.connect(d)));}
 public void state(String s,boolean connected){linkText=s;if(!connected){ready=false;pending=-1;ui.removeCallbacks(commandTimeout);stopRecord("连接中断");live.clear();lastSeq=-1;synth.disconnected();padText="等待打击垫";}if(connection!=null)connection.setText(s);if(padState!=null)padState.setText(padText);}
 static int u(byte b){return b&255;}static long u32(byte[] p,int at){return (u(p[at])|((long)u(p[at+1])<<8)|((long)u(p[at+2])<<16)|((long)u(p[at+3])<<24));}
 public void status(byte[] p){if(p.length!=20||u(p[0])!=0x53||u(p[1])!=1)return;boolean wasReady=ready;ready=ble.linked&&p[2]==1&&p[3]==1;decoded=u32(p,12);dropped=u32(p,16);if(recording&&(dropped!=recordDropped||!ready))incomplete=true;
  padText=ready?"打击垫就绪 · 已解析 "+decoded+" · 队列丢包 "+dropped:"C3 已连接，等待打击垫";if(padState!=null)padState.setText(padText);
  if(pending<0)requestId=u(p[4]);if(pending==u(p[4])&&u(p[5])>1){ui.removeCallbacks(commandTimeout);int r=u(p[5]);String[] labels={"","处理中","设备回读一致","打击垫未就绪","型号或键位模式不支持","设备写入失败","回读不一致","超时或断链，结果未确认"};resultText=operation+"："+(r<labels.length?labels[r]:"未知结果");pending=-1;if(result!=null)result.setText(resultText);toast(resultText);}
 }
 void command(int kind,int a,int b,int c,String name){if(!ready){toast("请先连接 C3，并等待打击垫就绪");return;}if(recording){toast("记录期间暂停配置修改");return;}if(pending>=0){toast("上一条命令仍在等待回读");return;}requestId=(requestId+1)&255;pending=requestId;operation=name;byte[] p={(byte)0x53,1,(byte)requestId,(byte)kind,(byte)a,(byte)b,(byte)c,0};int sum=0;for(int i=0;i<7;i++)sum+=u(p[i]);p[7]=(byte)~sum;resultText=name+"：正在核对与回读…";if(result!=null)result.setText(resultText);ui.postDelayed(commandTimeout,15000);ble.write(p);}
 void color(int r,int g,int b){command(1,r,g,b,"改色");}
 void keysPage(){auditCard();LinearLayout c=card("16 键映射");c.addView(text("编辑 MIDI 音符编号；先存为手机方案，再单独下发选中键。物理垫的编号与配置槽对应关系仍需逐垫核对。",14,MUTED));
  LinearLayout selectors=new LinearLayout(this);profileSpinner=new Spinner(this);bankSpinner=new Spinner(this);profileSpinner.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"预设 1","预设 2","预设 3","预设 4"}));bankSpinner.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"键组 1","键组 2","键组 3","键组 4","键组 5","键组 6","键组 7"}));profileSpinner.setSelection(profile);bankSpinner.setSelection(bank);selectors.addView(profileSpinner,new LinearLayout.LayoutParams(0,dp(48),1));selectors.addView(bankSpinner,new LinearLayout.LayoutParams(0,dp(48),1));c.addView(selectors);
  for(int row=0;row<4;row++){LinearLayout line=new LinearLayout(this);for(int col=0;col<4;col++){final int i=row*4+col;Button b=button("",()->selectKey(i));keyButtons[i]=b;LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(64),1);p.setMargins(dp(2),dp(3),dp(2),dp(3));line.addView(b,p);}c.addView(line);}
  noteInput=new EditText(this);noteInput.setTextColor(INK);noteInput.setInputType(2);noteInput.setHint("音符 0–127");c.addView(noteInput);selectKey(selected);
  c.addView(button("保存选中键到手机方案",()->{Integer n=parseNote();if(n==null)return;notes[selected]=n;getPreferences(0).edit().putInt("note"+selected,n).apply();selectKey(selected);toast("已保存到手机，尚未写入打击垫");}));
  c.addView(button("下发选中键并回读",()->{Integer n=parseNote();if(n==null)return;profile=profileSpinner.getSelectedItemPosition();bank=bankSpinner.getSelectedItemPosition();int slot=bank*16+selected;new AlertDialog.Builder(this).setTitle("写入单键音符").setMessage("预设 "+(profile+1)+" / 键组 "+(bank+1)+" / 键 "+(selected+1)+" → MIDI "+n+"。仅改音符字节，设备回读确认后才算成功。").setPositiveButton("写入",(d,w)->command(2,profile,slot,n,"键位修改")).setNegativeButton("取消",null).show();}));
  result=text(resultText,14,GREEN);c.addView(result);c.addView(button("导出手机键位方案",()->{try{JSONObject o=new JSONObject();o.put("format","starcluster-keymap-1");o.put("notes",new JSONArray(notes));export(o.toString(2),"starcluster-keymap.json");}catch(Exception e){error(e);}}));
 }
 Integer parseNote(){try{int n=Integer.parseInt(noteInput.getText().toString());if(n>=0&&n<=127)return n;}catch(Exception ignored){}toast("音符必须在 0–127 之间");return null;}
 void selectKey(int i){selected=i;for(int j=0;j<16;j++){keyButtons[j].setText((j+1)+"\n"+notes[j]);keyButtons[j].setBackground(background(j==i?GREEN:0xffd5c7b3,10));}noteInput.setText(""+notes[i]);}
 JSONObject validateScore(String source)throws Exception{JSONObject o=new JSONObject(source);if(!"starcluster-score-1".equals(o.optString("format")))throw new IOException("曲谱格式应为 starcluster-score-1");int tempo=o.getInt("bpm");if(tempo<20||tempo>300)throw new IOException("BPM 超出 20–300");JSONArray e=o.getJSONArray("events");if(e.length()>20000)throw new IOException("曲谱事件过多");long prev=-1;for(int i=0;i<e.length();i++){JSONObject x=e.getJSONObject(i);long t=x.getLong("at_ms"),duration=x.getLong("duration_ms");int note=x.getInt("note"),velocity=x.getInt("velocity");if(t<prev||t<0||t>3600000||duration<1||duration>60000||note<0||note>127||velocity<1||velocity>127)throw new IOException("第 "+(i+1)+" 个音符无效");prev=t;}return o;}
 int chosenSong=0,chosenPart=4;TextView rehearsalStatus;
 void refreshRehearsal(){
  if(rehearsalStatus==null)return;
  if(!synth.ready()||!synth.configured||synth.boardSong<0||synth.boardSong>=FpgaController.TITLES.length){
   rehearsalStatus.setText("等待板端曲目回读");return;
  }
  String mode=new String[]{"选曲","整曲","试听","学习","合奏"}[synth.mode];
  rehearsalStatus.setText("板端 · "+FpgaController.TITLES[synth.boardSong]+"　"+FpgaController.VOICES[synth.boardPart]+"\n"+mode+" · "+(synth.playing?"演奏中":"已停止")+(synth.cue<0?"":"　请敲 "+String.format(Locale.ROOT,"%02d",synth.cue)));
 }
 void scoreControls(){
  LinearLayout c=card("曲目合奏室");
  c.addView(text("选择曲目与声部，然后试听、跟灯或接手合奏。",14,MUTED));
  Spinner song=new Spinner(this),voice=new Spinner(this);
  song.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,FpgaController.TITLES));
  song.setSelection(chosenSong);c.addView(song);c.addView(voice);
  final ArrayList<Integer> ids=new ArrayList<>();
  Runnable voices=()->{ids.clear();ArrayList<String> names=new ArrayList<>();
   for(int i=0;i<16;i++)if((FpgaController.MASKS[chosenSong]&(1<<i))!=0){ids.add(i);names.add(FpgaController.VOICES[i]+" · 声部 "+String.format(Locale.ROOT,"%02d",i));}
   if(!ids.contains(chosenPart))chosenPart=ids.contains(4)?4:ids.get(0);
   voice.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,names));voice.setSelection(ids.indexOf(chosenPart));};
  voices.run();
  song.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onNothingSelected(AdapterView<?> p){}public void onItemSelected(AdapterView<?> p,View v,int i,long id){if(i!=chosenSong){chosenSong=i;voices.run();}}});
  voice.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){public void onNothingSelected(AdapterView<?> p){}public void onItemSelected(AdapterView<?> p,View v,int i,long id){if(i>=0&&i<ids.size())chosenPart=ids.get(i);}});
  String[] actions={"选中并停止","播放整曲","单听声部","跟灯练习","接手合奏"};
  for(int i=1;i<actions.length;i++){final int action=i;c.addView(button(actions[i],()->synth.rehearsal(chosenSong,chosenPart,action)));}
  c.addView(button("停止播放",()->synth.transport(true)));
  rehearsalStatus=text("",17,GREEN);c.addView(rehearsalStatus);refreshRehearsal();
 }
 void scorePage(){scoreControls();LinearLayout c=card("手机本地曲谱");c.addView(text(score==null?"尚未导入曲谱":score.optString("title","未命名曲谱")+"\n"+score.optInt("bpm")+" BPM · "+score.optJSONArray("events").length()+" 个音符",18,INK));c.addView(text("曲谱保存音符、时间和力度，不包含预录音频。下载后可离线保存在手机。",14,MUTED));
  c.addView(button("载入示例曲谱",()->{try{JSONArray events=new JSONArray();int[] melody={60,64,67,72,67,64,62,60};for(int i=0;i<melody.length;i++){JSONObject e=new JSONObject();e.put("at_ms",i*500);e.put("duration_ms",400);e.put("note",melody[i]);e.put("velocity",90);events.put(e);}JSONObject s=new JSONObject();s.put("format","starcluster-score-1");s.put("title","星群 · 八音练习");s.put("bpm",120);s.put("events",events);saveScore(s.toString());}catch(Exception e){error(e);}}));
  c.addView(button("从文件导入 JSON 曲谱",()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.setType("*/*");i.addCategory(Intent.CATEGORY_OPENABLE);startActivityForResult(i,20);}));
  EditText url=new EditText(this);url.setTextColor(INK);url.setHintTextColor(MUTED);url.setHint("HTTPS 曲谱文件地址");url.setInputType(17);c.addView(url);c.addView(button("在线下载曲谱",()->downloadScore(url.getText().toString().trim())));
  c.addView(button("查看 / 导出曲谱",()->{if(score==null){toast("请先载入曲谱");return;}try{new AlertDialog.Builder(this).setTitle(score.optString("title","曲谱")).setMessage(score.toString(2)).setPositiveButton("导出",(d,w)->export(score.toString(),"starcluster-score.json")).setNegativeButton("关闭",null).show();}catch(Exception e){error(e);}}));

 }
 void saveScore(String source)throws Exception{JSONObject validated=validateScore(source);writeLocal("score.json",validated.toString());score=validated;toast("曲谱已校验并保存到手机");render();}
 String readBounded(InputStream in)throws IOException{ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] p=new byte[4096];int n;while((n=in.read(p))!=-1){if(b.size()+n>1024*1024)throw new IOException("文件不能超过 1 MB");b.write(p,0,n);}return b.toString("UTF-8");}
 void downloadScore(String address){try{URL u=new URL(address);if(!u.getProtocol().equals("https"))throw new IOException("请使用 HTTPS 曲谱地址");toast("正在下载…");new Thread(()->{HttpURLConnection c=null;try{c=(HttpURLConnection)u.openConnection();c.setInstanceFollowRedirects(false);c.setConnectTimeout(10000);c.setReadTimeout(10000);if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode()+"；请使用文件最终地址");String s;try(InputStream in=c.getInputStream()){s=readBounded(in);}validateScore(s);ui.post(()->{try{saveScore(s);}catch(Exception e){error(e);}});}catch(Exception e){ui.post(()->error(e));}finally{if(c!=null)c.disconnect();}},"score-download").start();}catch(Exception e){error(e);}}
 public void midi(byte[] p){if(p.length!=13||u(p[0])!=0x4d||u(p[1])!=1)return;long seq=u32(p,2),time=u32(p,6);int s=u(p[10]),a=u(p[11]),b=u(p[12]);auditHit(s,a,b);boolean gap=lastSeq>=0&&seq!=((lastSeq+1)&0xffffffffL);lastSeq=seq;int k=s&240;String type=k==144&&b>0?"按下":k==128||k==144?"松开":k==208?"通道压力":k==176?"控制变化":k==192?"程序切换":"其他消息";midiText=type+"  ·  通道 "+((s&15)+1)+"\n音符 / 数据 "+a+"  ·  力度 / 数据 "+b+"\n事件 #"+seq;if(activityText!=null)activityText.setText(midiText);
  int key=((s&15)<<8)|a;if(k==144&&b>0)live.add(key);if(k==128||(k==144&&b==0))live.remove(key);
  if(recording){if(recorded.length()>=100000){incomplete=true;stopRecord("事件数量上限");return;}if(gap)incomplete=true;try{JSONObject e=new JSONObject();e.put("sequence",seq);e.put("c3_ms",time);e.put("phone_ms",SystemClock.elapsedRealtime()-recordStart);e.put("status",s);e.put("data1",a);e.put("data2",b);recorded.put(e);recordLast=seq;if(recordFirst<0)recordFirst=seq;}catch(Exception ex){incomplete=true;}updateRecord();}
 }
 void recordPage(){LinearLayout c=card("演奏事件回传");c.addView(text("逐条接收打击垫的音符、力度与触后事件。序号缺失、蓝牙断开或切到后台会标记记录不完整。",14,MUTED));recordState=text("",17,GREEN);c.addView(recordState);recordButton=button(recording?"结束并保存记录":"开始记录",()->{if(recording){stopRecord("");return;}if(!ready||ble.events==null){toast("需要已连接的 C3 v5 和打击垫");return;}if(pending>=0){toast("请等待配置写入完成");return;}recorded=new JSONArray();recording=true;incomplete=!live.isEmpty();recordDropped=dropped;recordFirst=recordLast=-1;recordStart=SystemClock.elapsedRealtime();updateRecord();});c.addView(recordButton);c.addView(button("导出最近一次记录",()->{try{JSONObject take=lastTake;if(take==null){String s=readLocal("take.json");if(s!=null)take=new JSONObject(s);}if(take==null){toast("尚无已保存记录");return;}export(take.toString(2),"starcluster-events.json");}catch(Exception e){error(e);}}));updateRecord();
  c=card("音频录音回传 · 待实现");c.addView(text("事件记录不等同 WAV 音频录音。题目中的录音回传仍需接通 FPGA 音频采集、存储与文件传输，并验证声音文件。当前应用不使用手机麦克风冒充 FPGA 录音。",14,MUTED));
 }
 void updateRecord(){if(recordState!=null)recordState.setText((recording?"正在接收":"已停止")+" · "+recorded.length()+" 条事件"+(incomplete?"\n完整性告警":""));if(recordButton!=null)recordButton.setText(recording?"结束并保存记录":"开始记录");}
 void stopRecord(String reason){if(!recording)return;recording=false;if(!reason.isEmpty()||!live.isEmpty()||(recordLast>=0&&decoded>recordLast))incomplete=true;try{JSONObject o=new JSONObject();o.put("format","starcluster-midi-events-1");o.put("kind","event_recording_not_audio");o.put("duration_ms",SystemClock.elapsedRealtime()-recordStart);o.put("incomplete",incomplete);o.put("stop_reason",reason);o.put("start_state","held notes before connection are unknown");o.put("events",recorded);lastTake=o;writeLocal("take.json",o.toString());}catch(Exception e){error(e);}updateRecord();}
 void export(String s,String name){exportText=s;Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");i.putExtra(Intent.EXTRA_TITLE,name);startActivityForResult(i,21);}
 @Override public void onActivityResult(int request,int response,Intent data){super.onActivityResult(request,response,data);if(response!=RESULT_OK||data==null||data.getData()==null)return;Uri uri=data.getData();try{if(request==20){try(InputStream in=getContentResolver().openInputStream(uri)){saveScore(readBounded(in));}}else if(request==21){try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){out.write(exportText.getBytes(StandardCharsets.UTF_8));}toast("导出完成");}}catch(Exception e){error(e);}}
 String readLocal(String name)throws IOException{File f=new File(getFilesDir(),name);if(!f.exists())return null;try(InputStream in=new FileInputStream(f)){return readBounded(in);}}
 void writeLocal(String name,String s)throws IOException{File temp=new File(getFilesDir(),name+".tmp");try(FileOutputStream out=new FileOutputStream(temp)){out.write(s.getBytes(StandardCharsets.UTF_8));out.getFD().sync();}if(!temp.renameTo(new File(getFilesDir(),name)))throw new IOException("保存失败");}
 void toast(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}void error(Exception e){toast("操作失败："+e.getMessage());}
 public void fpga(byte[] p){synth.receive(p);}
 void updateFpga(){refreshRehearsal();if(fpgaState!=null)fpgaState.setText(synth.state+"\n"+(synth.playing?"板载曲目播放中":"板载曲目已停止")+" · 活跃声部 "+synth.active+"\n当前轨归属："+(synth.owner==3?"手机":synth.owner==0?"自动 / 空闲":"其他席位 "+synth.owner));}
 void playPage(){LinearLayout c=card("板载演奏");fpgaState=text("",16,GREEN);c.addView(fpgaState);updateFpga();c.addView(text("声音从解码板接到音箱。在「曲谱」页选歌与声部。实体垫使用预设四、键组二。",13,MUTED));c.addView(button("开始板载曲目",()->synth.transport(false)));c.addView(button("停止板载曲目",()->synth.transport(true)));c.addView(button("停止手机全部音符",()->synth.release()));
  c=card("触摸演奏 · 席位 3");Spinner part=new Spinner(this);part.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"底鼓","军鼓","踩镲","贝斯","电钢琴","簧管","主奏","合唱","拨弦","笛","钟","木琴","弓弦","管风琴","铜管","电子歌手（需麦克风）"}));part.setSelection(synth.part);part.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onItemSelected(android.widget.AdapterView<?> p,View v,int position,long id){if(position!=synth.part)synth.select(position);}public void onNothingSelected(android.widget.AdapterView<?> p){}});c.addView(part);
  c.addView(text("按住发声，松开释放。音高使用手机保存的16键方案。",13,MUTED));
  for(int row=0;row<4;row++){LinearLayout line=new LinearLayout(this);for(int col=0;col<4;col++){final int key=(3-row)*4+col;Button b=button((key+1)+"\n"+notes[key],()->{});b.setOnTouchListener((v,e)->{int action=e.getActionMasked();if(action==MotionEvent.ACTION_DOWN){v.getParent().requestDisallowInterceptTouchEvent(true);b.setAlpha(.55f);synth.down(key,notes[key],velocity);return true;}if(action==MotionEvent.ACTION_UP||action==MotionEvent.ACTION_CANCEL){b.setAlpha(1);synth.up(key);v.getParent().requestDisallowInterceptTouchEvent(false);return true;}return true;});LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,dp(65),1);p.setMargins(dp(2),dp(3),dp(2),dp(3));line.addView(b,p);}c.addView(line);}
  TextView level=text("力度："+velocity,14,MUTED);c.addView(level);SeekBar force=new SeekBar(this);force.setMax(126);force.setProgress(velocity-1);force.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int value,boolean user){velocity=value+1;level.setText("力度："+velocity);}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){}});c.addView(force);
  c.addView(button("申请当前声部控制权",()->synth.claim()));c.addView(text("表情强度：松开滑块后发送；需要归属显示为手机。",13,MUTED));SeekBar expression=new SeekBar(this);expression.setMax(127);expression.setProgress(127);expression.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){public void onProgressChanged(SeekBar s,int value,boolean user){}public void onStartTrackingTouch(SeekBar s){}public void onStopTrackingTouch(SeekBar s){synth.parameter(0,s.getProgress());}});c.addView(expression);
 }
 @Override public void onResume(){super.onResume();if(synth!=null)synth.start();}
 @Override public void onStop(){super.onStop();stopRecord("应用进入后台");if(synth!=null)synth.pause();}
 @Override public void onDestroy(){ble.close();ui.removeCallbacksAndMessages(null);super.onDestroy();}
}
