"""Native 800x480 score pages and their shared 8x8 antialiased tile atlas."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PAPER,INK,RED,GRID,GOLD="#faf5e9","#292722","#a33727","#d5c7b3","#fac751"
PALETTE=[PAPER,"#e9dfcf",GRID,"#84796b",INK,"#d49b86",RED,GOLD]
def make(out):
    fonts={}
    def text(im,x,y,label,size,fill=INK,anchor="mm",latin=False):
        key=(size,latin)
        if key not in fonts:
            fonts[key]=ImageFont.truetype("C:/Windows/Fonts/"+("georgia.ttf" if latin else "simsun.ttc"),size)
        ImageDraw.Draw(im).text((x,y),label,font=fonts[key],fill=fill,anchor=anchor,stroke_width=0)
    palette=Image.new("P",(1,1))
    from PIL import ImageColor
    rgb=[ImageColor.getrgb(c) for c in PALETTE]
    palette.putpalette(bytes(v for c in rgb+[rgb[0]]*(256-len(rgb)) for v in c))
    atlas={};rows=[];maps=[]
    def add(im):
        im=im.quantize(palette=palette,dither=Image.Dither.NONE)
        start=len(maps)
        for y in range(0,im.height,8):
            for x in range(0,im.width,8):
                tile=bytes(b if b<8 else 0 for b in im.crop((x,y,x+8,y+8)).tobytes())
                if tile not in atlas:
                    atlas[tile]=len(atlas)
                    for j in range(0,64,8):
                        rows.append(sum(k<<(3*i) for i,k in enumerate(tile[j:j+8])))
                maps.append(atlas[tile])
        return start
    def base(page):
        im=Image.new("RGB",(800,480),PAPER);d=ImageDraw.Draw(im)
        d.polygon([(36,10),(39,21),(50,25),(39,28),(36,40),(33,28),(22,25),(33,21)],fill=RED)
        text(im,63,25,"星群",25,anchor="lm")
        text(im,196,24,"总音量",18,anchor="lm")
        titles=["演奏","频谱","立体声","曲目"]
        for i,n in enumerate(titles):
            x=504+i*76;text(im,x,25,n,18,RED if page==i else INK)
            if i==page:d.line((x-21,40,x+21,40),fill=RED,width=3)
        d.line((20,49,780,49),fill=GRID);d.line((20,443,780,443),fill=GRID)
        text(im,22,461,"星群电子乐器",14,anchor="lm");text(im,775,461,f"{page+1:02d} / 04",16,RED,"rm",True)
        return im,d
    for p in range(4):
        im,d=base(p)
        if p==0:
            text(im,40,99,"声部表情",20,anchor="lm")
            text(im,544,89,"起音",18,anchor="lm")
            text(im,544,132,"释音",18,anchor="lm")
            text(im,400,155,"声部",16,RED)
            for x,t in [(100,"音高"),(355,"力度"),(615,"速度")]:text(im,x,188,t,21)
            for y in range(232,289,14):d.line((38,y,762,y),fill=GRID)
            for i,t in enumerate(["弯音","亮度","声像","回声"]):
                x=40+(i%2)*375;y=332+(i//2)*60;text(im,x,y,t,21,anchor="lm")
                d.line((x+74,y,x+318,y),fill=GRID,width=3)
        if p==1:
            text(im,400,109,"实时频谱",48)
            text(im,400,157,"频带能量",18,RED)
            for y in range(212,373,40):d.line((64,y,736,y),fill=GRID)
            for x,t in [(64,"低频"),(400,"中频"),(736,"高频")]:text(im,x,402,t,18)
        if p==2:
            text(im,400,98,"立体声",46);text(im,400,147,"李萨如图形",18,RED)
            for x in range(88,345,32):d.line((x,169,x,425),fill=GRID)
            for y in range(169,426,32):d.line((88,y,344,y),fill=GRID)
            for x,t in [(485,"左声道"),(645,"右声道")]:
                text(im,x,193,t,22);d.rectangle((x-18,222,x+18,398),outline=GRID,width=2)
        if p==3:
            text(im,400,144,"曲目与学习",19,RED)
            for i in range(16):
                x=50+i%4*76;y=172+(3-i//4)*62
                d.rounded_rectangle((x,y,x+66,y+54),6,outline=GRID,width=2)
                text(im,x+33,y+27,f"{i+1:02d}",23,latin=True)
            text(im,430,183,"当前目标",20,anchor="lm");text(im,430,308,"伴奏进度",20,anchor="lm")
            d.line((430,348,750,348),fill=GRID,width=3)
            text(im,430,381,"下一垫",16,RED,anchor="lm")
            d.line((430,420,748,420),fill=GRID);d.line((460,410,460,430),fill=RED,width=2)
        add(im)
    def sprites(labels,w,h,size,latin=False):
        start=None
        for label in labels:
            im=Image.new("RGB",(w,h),PAPER);text(im,w//2,h//2-1,label,size,INK,latin=latin)
            index=add(im)
            if start is None:start=index
        return start
    names=['底鼓','军鼓','踩镲','贝斯','电钢琴','簧管','主奏','合唱','拨弦','笛','钟','木琴','弓弦','管风琴','铜管','电子歌手']
    offsets={'PART':sprites(names,240,64,48),'SONG':sprites(['小星星','欢乐颂','星群·合流','四类乐器示范','音阶与和弦练习'],352,64,44),
             'DIGIT':sprites('0123456789',16,32,26,True), 'NOTE':sprites([('C','C♯','D','E♭','E','F','F♯','G','A♭','A','B♭','B')[i%12]+str(i//12-1) for i in range(128)],64,32,23,True),'MODE':sprites(['整曲播放','声部试听','接手合奏','跟灯练习'],160,32,23)}
    assert len(atlas)<4096
    blocks=list(dict.fromkeys(tuple(maps[i:i+8]) for i in range(0,len(maps),8)))
    block_id={b:i for i,b in enumerate(blocks)}
    unique_rows=list(dict.fromkeys(rows));row_id={r:i for i,r in enumerate(unique_rows)}
    assert len(unique_rows)<4096 and len(blocks)<2048
    def mem(name,values,digits):
        (out/name).write_text(''.join(f'{v:0{digits}x}\n' for v in values))
    mem('score_map.mem',(block_id[tuple(maps[i:i+8])] for i in range(0,len(maps),8)),3)
    mem('score_tiles.mem',(v for block in blocks for v in block),3)
    mem('score_rows.mem',(row_id[r] for r in rows),4)
    mem('score_pixels.mem',unique_rows,6)
    # Gowin maps a monolithic >16K row index to LUTs. Six bounded banks
    # use native 4096x4 ROM modes with no change in pixel latency.
    index=[row_id[r] for r in rows]
    declarations=[];choices=[]
    for bank,base in enumerate(range(0,len(index),4096)):
        chunk=index[base:base+4096]
        file=f'score_rows_{bank}.mem'
        mem(file,chunk+[0]*(4096-len(chunk)),3)
        declarations.append(f'reg[11:0]rom{bank}[0:4095]; reg[11:0]q{bank}; initial $readmemh("{file}",rom{bank}); always @(posedge clk)q{bank}<=rom{bank}[row_address[11:0]];')
        choices.append(f"3'd{bank}:row_id=q{bank};")
    (out/'rtl/row_banks.vh').write_text('\n'.join(declarations)+'\nreg[2:0]bank_id;always @(posedge clk)bank_id<=row_address[14:12];\nalways @* case(bank_id)\n'+'\n'.join(choices)+'\ndefault:row_id=0;endcase\n')
    tile_data=[v for block in blocks for v in block]
    declarations=[];choices=[]
    for bank,base in enumerate(range(0,len(tile_data),4096)):
        chunk=tile_data[base:base+4096]
        file=f'score_tiles_{bank}.mem'
        mem(file,chunk+[0]*(4096-len(chunk)),3)
        declarations.append(f'reg[11:0]tile_rom{bank}[0:4095];reg[11:0]tile_q{bank};initial $readmemh("{file}",tile_rom{bank});always @(posedge clk)tile_q{bank}<=tile_rom{bank}[tile_address[11:0]];')
        choices.append(f"2'd{bank}:tile=tile_q{bank};")
    (out/'rtl/tile_banks.vh').write_text('\n'.join(declarations)+'\nreg[1:0]tile_bank;always @(posedge clk)tile_bank<=tile_address[13:12];\nalways @* case(tile_bank)\n'+'\n'.join(choices)+'\ndefault:tile=0;endcase\n')
    block_data=[block_id[tuple(maps[i:i+8])] for i in range(0,len(maps),8)]
    declarations=[];choices=[]
    for bank,base in enumerate(range(0,len(block_data),4096)):
        chunk=block_data[base:base+4096]
        file=f'score_blocks_{bank}.mem'
        mem(file,chunk+[0]*(4096-len(chunk)),3)
        declarations.append(f'reg[10:0]block_rom{bank}[0:4095];reg[10:0]block_q{bank};initial $readmemh("{file}",block_rom{bank});always @(posedge clk)block_q{bank}<=block_rom{bank}[block_address[11:0]];')
        choices.append(f"1'd{bank}:block_id=block_q{bank};")
    (out/'rtl/block_banks.vh').write_text('\n'.join(declarations)+'\nreg block_bank;always @(posedge clk)block_bank<=block_address[12];\nalways @* case(block_bank)\n'+'\n'.join(choices)+'\ndefault:block_id=0;endcase\n')
    (out/'rtl/score_layout.vh').write_text('localparam SHOW_PARAMETERS=1, ATTACK_NUMERIC=1;\n'+''.join(f'localparam {k}_BASE={v};\n' for k,v in offsets.items())+f'localparam MAP_SIZE={len(maps)//8},TILE_SIZE={len(blocks)*8},ROW_SIZE={len(rows)},PIX_SIZE={len(unique_rows)};\n')
    print('score tiles:',len(atlas),'map entries:',len(maps))
