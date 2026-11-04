from pathlib import Path
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

ROOT=Path(__file__).parent
doc=Document()
sec=doc.sections[0]
sec.page_height=Cm(29.7); sec.page_width=Cm(21)
sec.top_margin=Cm(1.8); sec.bottom_margin=Cm(1.7)
sec.left_margin=Cm(2); sec.right_margin=Cm(2)
sec.header_distance=Cm(.8); sec.footer_distance=Cm(.8)
for name,size in [('Normal',10.5),('Title',25),('Subtitle',12),('Heading 1',18),('Heading 2',13),('Heading 3',11)]:
    s=doc.styles[name]; s.font.name='Microsoft YaHei'; s.font.size=Pt(size); s.font.color.rgb=RGBColor(0,0,0)
    s._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    s.paragraph_format.space_after=Pt(7)
    s.paragraph_format.line_spacing=1.18
doc.styles['Normal'].paragraph_format.widow_control=True
doc.styles['Subtitle'].font.italic=False
for style in doc.styles:
    for border in list(style._element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
header=sec.header.paragraphs[0]; header.text='Tang Mega 138K Pro  开发与时序入门'; header.style='Caption'
header.runs[0].font.color.rgb=RGBColor(0,0,0)
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('Tang Mega 138K Pro  |  ')
field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); footer._p.append(field)
for r in footer.runs:r.font.size=Pt(8)
doc.core_properties.title='Tang Mega 138K Pro 开发指南'
doc.core_properties.subject='硬件分区 开发环境 运行流程与时序'
doc.core_properties.author=''
def p(t='',style=None): return doc.add_paragraph(t,style)
def h(t):doc.add_heading(t,2)
def page(t,major=False):
    heading=doc.add_heading(t,1 if major else 2)
    heading.paragraph_format.page_break_before=True
def table(headers,rows,widths):
    t=doc.add_table(rows=1,cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    for i,w in enumerate(widths):t.columns[i].width=Cm(w)
    for i,s in enumerate(headers):t.rows[0].cells[i].text=s
    for row in rows:
        cells=t.add_row().cells
        for c,s in zip(cells,row):c.text=s
    for j,row in enumerate(t.rows):
        trpr=row._tr.get_or_add_trPr()
        if j==0:trpr.append(OxmlElement('w:tblHeader'))
        trpr.append(OxmlElement('w:cantSplit'))
        for i,c in enumerate(row.cells):
            c.width=Cm(widths[i]); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            pr=c._tc.get_or_add_tcPr(); sh=OxmlElement('w:shd'); sh.set(qn('w:fill'),'DDE8EF' if j==0 else ('F5F7F9' if j%2==0 else 'FFFFFF'));pr.append(sh)
            mar=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                el=OxmlElement('w:'+side);el.set(qn('w:w'),'85');el.set(qn('w:type'),'dxa');mar.append(el)
            pr.append(mar)
            borders=OxmlElement('w:tcBorders')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            pr.append(borders)
            for pa in c.paragraphs:
                pa.paragraph_format.space_after=Pt(2);pa.paragraph_format.line_spacing=1.1
                for r in pa.runs:r.font.size=Pt(9);r.bold=j==0
    p('')
def code(t):
    pa=p(t);pa.paragraph_format.line_spacing=1.0;pa.paragraph_format.space_after=Pt(8)
    for r in pa.runs:r.font.name='Consolas';r.font.size=Pt(9)
def cap(t):
    pa=p(t);pa.paragraph_format.space_after=Pt(8)
    for r in pa.runs:r.font.size=Pt(8.5);r.font.color.rgb=RGBColor.from_string('555555')
def flow(items):
    for i,(title,body) in enumerate(items):
        pa=p();pa.add_run(f'{i+1:02d}  {title}').bold=True
        p(body)
        if i<len(items)-1:
            pa=p('↓');pa.alignment=WD_ALIGN_PARAGRAPH.CENTER;pa.paragraph_format.space_after=Pt(0)

p('Tang Mega 138K Pro\n开发指南','Title')
p('面向有单片机基础的读者','Subtitle')
p('本指南说明板卡各区域的作用、开发所需环境，以及 FPGA 从硬件描述到上电运行的完整过程。重点解释时钟、逻辑门和寄存器怎样共同决定时序。纯 FPGA 逻辑开发无需先使用板内的 RISC-V 处理器。')
doc.add_heading('1 板卡正面与功能分区',1)
doc.add_picture(str(ROOT/'assets/official_top.png'),width=Cm(17))
cap('图 1  Tang Mega 138K Pro 正面官方实物图。图片来源：Sipeed Wiki [1]。下文位置描述均以本图方向为准；板卡修订和散热器安装状态可能影响外观。')
p('中央带 FPGA 的小板是核心板（SOM），外围较大的黑色板是 Pro Dock 底板。核心板提供运算、存储和部分供电；底板把信号引出到 USB、视频、网口、光口和排针等连接器。')
p('阅读顺序：先对照第 2 页识别接口，再阅读第 4 页的开发环境，最后从第 6 页理解运行流程。时序与逻辑门的专门说明从第 8 页开始。')
cap('资料核对日期 2026 年 10 月 6 日  |  正文共三个部分  |  官方资料链接见文末')

page('1.1 按位置认识板卡')
p('下表对应图 1 上可辨认的主要区域。接口外形相似不代表用途相同，接线时应同时核对板上丝印与原理图。[1][2]')
table(['位置与丝印','区域名称','功能与使用方式'],[
('中央小板','FPGA 核心板','GW5AST 系列 FPGA 是电路实现主体；核心板还集成 DDR3、Flash 和电源电路。'),
('左上两个视频座\nDVI TX / DVI RX','视频输出与输入','使用 HDMI 外形连接器传输例程规定的视频信号。发送端接显示设备，接收端接视频源；物理接口不代表已实现完整 HDMI 功能。'),
('左侧中部\n1GbE RJ45','千兆以太网接口','通过板载 PHY 与 FPGA 交换数据；协议处理、MAC 或 UDP 等逻辑由工程实现。'),
('左侧下部\nSFP 0 / SFP 1','两个 SFP+ 插槽','连接兼容的光模块或线缆；与高速收发器和相应 PHY、协议逻辑配合使用。'),
('底边金手指\n138K PRO DOCK','PCIe 接口','与主机交换高速数据；需要匹配的 FPGA 工程及主机驱动。主机和板卡断电后插拔。'),
('右上角\nDC12V INPUT / POWER SW','电源输入与开关','为整板供电并控制开关状态。12V 输入针对底板电源口，不可接到核心板或 GPIO 供电引脚。'),
('右侧上方 USB-C\nSOFT USB','自定义 USB 接口','供用户 USB 逻辑使用，并非默认的下载口；官方说明该口不能给整板供电。'),
('右侧下方 USB-C\nJTAG UART','下载与串口调试接口','连接电脑，用于 JTAG 配置 FPGA 和 UART 通信。UART 数据内容由用户设计决定。'),
('顶边左侧\nS0 至 S3','四个按键','用于复位、模式选择或交互。具体用途、有效电平由电路连接和工程定义。'),
('顶边黑色排针与 ADC 标识','PMOD 扩展和 ADC 接入区','扩展数字外设或模拟采样连接。应分别核对 GPIO 电平与 ADC 输入量程，不能混为一谈。'),
('顶边右侧\nMIPI CSI0 / CSI1','摄像头连接区','接兼容的 MIPI 摄像头；需要对应时钟、控制接口与图像接收工程。'),
('底边右侧长排针\n右侧音频与风扇座','40P 扩展及音频散热区','排针扩展用户信号；音频座连接相应音频电路；5V FAN 座用于风扇。接线以具体针脚定义为准。')
],[4.2,3.3,9.5])
cap('并非所有元件都能从正面照片看到。被核心板遮挡、位于背面或小尺寸器件的准确位置，需要对照 PCB 位号图和原理图，而不是仅凭照片猜测。')

page('1.2 核心资源与板内连接')
table(['资源','用途','与单片机的对应理解'],[
('LUT 与寄存器','LUT 实现组合逻辑；寄存器保存每拍状态。','可按设计构造计数器、状态机、并行计算和接口控制器。'),
('DSP 与片内 BSRAM','DSP 适合乘加运算；BSRAM 存储缓存、表格或 FIFO 数据。','类似专用运算单元和片内 RAM，但需通过硬件逻辑连接。'),
('两颗 DDR3\n合计 1 GB','较大容量的数据缓存，例如图像帧或采样数据。','类似外部 RAM；需要控制器初始化和校准，不能当普通寄存器直接访问。'),
('两颗 SPI NOR Flash\n各 128 Mbit','保存非易失数据或相应启动映像。','类似存放固件的 Flash；写入哪一颗、地址及用途取决于设计。'),
('PLL 与时钟网络','产生或分配设计所需时钟，降低时钟分配偏斜。','对应时钟树和 PLL；不会因为 RTL 写了频率数值就自动改变时钟。'),
('AE350 RISC-V 硬核','为软硬件协同提供处理器。','这里才涉及 C 程序、指令执行、软件编译器和处理器启动。')
],[4.1,6.5,6.4])
p('核心板的 FPGA 通过板间连接器访问底板外设。片内 LUT、寄存器、DSP 和 RAM 构成数据通路，DDR3 或外部 Flash 则要经过相应控制器。引脚电平和连接关系由硬件固定，逻辑功能由配置决定。[2][3]')
h('把整板看成四条通路')
p('供电通路：底板电源输入 → 电源转换 → FPGA 核心、电气接口和外设。时钟通路：振荡源或参考时钟 → PLL 与时钟网络 → 各逻辑模块。配置通路：电脑 JTAG 或启动存储器 → FPGA 配置存储器。业务数据通路：输入接口 → 接收与处理逻辑 → 缓存 → 输出接口。')
p('其余板载资源还包括用户 LED、WS2812、RGB 屏幕与 DVP 接口、麦克风阵列接口、SD 卡、EEPROM，以及预留的 M.2 座等。接口存在不等于系统已经支持插入的设备，通常还需要控制器、协议逻辑、引脚约束及适配的例程。[1][4]')
h('资料版本应怎样判断')
p('早期 v1.0 核心板规格书包含 GW5AT 与 PCIe 2.0 等表述；较新 Wiki 标注 GW5AST，且芯片与底板表格对 PCIe 速率的口径也不同。本文不据此承诺某一链路速率。设计高速接口时，应以实物器件、PCB 版本、所用 IP 和验证过的工程为准，并区分芯片上限、板上布线与实际协商速率。[1][2][3]')

page('2 开发所需环境',True)
p('下面给出一套 Windows 开发环境的组成。它适用于文档读者自行准备电脑，不包含任何特定电脑的设置。电脑容量为使用建议，不是厂商最低配置声明。')
table(['类别','所需内容','选择说明'],[
('电脑','64 位 Windows 电脑、USB 数据口','选择所下载 IDE 发布说明支持的系统。建议 16 GB 及以上内存、SSD 和至少 20 GB 可用空间，复杂工程可进一步增加。'),
('板卡与连接','138K Pro 核心板及 Pro Dock、匹配电源、USB 数据线','整板按 DC12V INPUT 标识和官方要求供电；USB 数据线接 JTAG UART 口。基础逻辑开发通常无需额外购买下载器。'),
('综合与实现工具','GOWIN EDA 商业版','用于工程管理、综合、布局布线和生成配置文件；确认支持 GW5AST-138 及实际器件版本。'),
('授权','对应工具与器件的有效 License','单机型或共享型按申请条件配置。授权范围和有效期以收到的许可为准。'),
('下载工具','GOWIN Programmer','建议优先使用与开发环境配套的版本，完成器件扫描、SRAM 下载或 Flash 烧写。'),
('USB 驱动','板载 USB JTAG/UART 所需驱动','该板官方排查文档提到 FT2232 和 USB Serial Converter A/B；应遵循当前下载工具的驱动安装说明。'),
('资料与工程','官方原理图、引脚约束、例程和器件手册','必须对应 Pro 版本和实际 PCB；不要直接套用标准版或其他 Tang 板卡的约束。'),
('可选仿真调试','HDL 仿真器、波形查看器、串口终端、GAO','行为仿真可选择合适的开源或商业工具；含厂商 IP 时需相应仿真库与工具兼容支持。')
],[3.0,5.4,8.6])
h('版本选择与下载入口')
p('截至资料核对日，高云软件下载页列出 Windows 版 V1.9.12.04。Sipeed 板卡文档要求 138K Pro 使用 V1.9.9 或更新的商业版，并提示 V1.9.10.02 Programmer 存在下载问题。新版是否适配某个旧工程，还应阅读其发布说明和例程说明，不能仅凭版本号保证兼容。[1][5]')
p('官方下载与 License 申请：https://www.gowinsemi.com.cn/software/1\n官方示例：https://github.com/sipeed/TangMega-138KPro-example')

page('2.1 环境配置与工程文件')
h('安装和授权顺序')
p('先下载支持目标器件的 IDE 与 Programmer，安装工具及对应 USB 驱动；再配置 License。单机授权应使用授权工具识别的本机 Host ID 或 MAC 提交申请，并按许可说明加载文件。共享授权则配置服务器和端口，并保持网络可达。不要从蓝牙、VPN 或虚拟网卡中随意选一个地址。')
p('连接板卡后，电脑经 JTAG UART 口访问板载调试器；Programmer 扫描到目标器件之后才具备下载条件。若出现 No USB Cable Connection，依次核对数据线、接口、供电和驱动；若器件不匹配，则检查工程器件设置及下载链，而不是反复烧写。')
h('新工程必须明确的设置')
p('目标器件应与实际 FPGA 的完整型号、封装、速度等级和器件版本一致。Sipeed 页面给出的系列型号为 GW5AST-LV138FPG676A，IDE 封装名称为 FCPBG676A，器件版本需区分 B/C。先核对板卡与官方工程，再设置顶层模块、源文件和约束。[1]')
table(['文件或对象','含义','容易混淆的地方'],[
('.v / .sv / .vhd','描述逻辑功能与寄存器行为的源文件。','不是直接供 FPGA 按行执行的机器指令。'),
('testbench','仿真激励和检查逻辑。','通常不作为板上硬件综合；仿真中的延时不能照搬成硬件定时。'),
('.cst','管脚位置及端口电气等物理约束。','顶层端口名必须一致，并确认 VCCIO、电平标准、有效电平。'),
('.sdc','时钟、输入输出时序及必要的时序例外。','告诉工具需要分析什么，不会自动制造真实时钟或修复电路。'),
('.gprj 与 IP 配置','工程组织、目标设置及 IP 参数。','更换软件版本时可能需要重新生成 IP。'),
('.fs','实现后生成的 FPGA 配置码流。','下载到 SRAM 与写入 Flash 的持久性不同。')
],[3.2,6.3,7.5])
h('时钟约束的最小示意')
code('create_clock -name sys_clk -period 20 [get_ports {clk}]')
p('这条命令声明 clk 端口时钟周期为 20 ns，即 50 MHz。它只适用于实际输入确为 50 MHz 的情形；端口名及周期要改成真实设计值。外设接口还需根据外部器件时序添加输入输出延迟，PLL 派生时钟也需正确建模。[6]')

page('3 从硬件描述到板上运行',True)
p('单片机常见流程是“编译 C 程序 → 写入 Flash → CPU 逐条取指”。FPGA 逻辑设计则是“描述电路 → 实现电路 → 配置电路”。配置完成后，多个硬件模块可以同时工作，寄存器在各自时钟边沿更新。')
flow([
('描述功能与接口','编写 RTL，明确输入输出、状态、计算关系和时钟复位；准备管脚及时间要求。'),
('仿真逻辑行为','testbench 提供输入，观察输出和状态随时钟变化。仿真检查功能，但普通 RTL 仿真不能代替布局布线后的时序分析。'),
('综合成硬件资源','工具把表达式、条件和寄存器描述转换为 LUT、触发器、RAM、DSP 等资源连接，并进行优化。'),
('布局布线与时序分析','为资源选择芯片内位置及连接线路；检查数据能否在规定的采样时刻前到达。必要时修改结构或约束后重新实现。'),
('生成码流并下载','工具输出配置文件，经 Programmer 写入 FPGA SRAM，或按正确启动方案写入外部 Flash。'),
('配置后的电路持续运行','配置位确定 LUT 内容、布线和资源模式。输入信号经过组合逻辑传播，时钟推动寄存器更新，输出驱动外设。')
])
cap('图 2  FPGA 开发流程示意。箭头表示开发顺序；不表示 FPGA 运行时逐条执行这些步骤。')

page('3.1 上电启动与程序的两种含义')
h('上电后发生什么')
p('整板电源建立后，器件完成内部上电复位。在启动模式、目标 Flash 和映像设置正确的前提下，FPGA 可从非易失存储器加载配置；开发时也可以由电脑通过 JTAG 加载。配置完成后，设计需按要求等待时钟及相关模块稳定，并在相应时钟域安全释放复位。用到 DDR3 等外设时，还需等待初始化或校准完成，再开放业务数据通路。')
p('这些过程并不全由 FPGA 自动替用户完成：例如业务状态机何时启动、如何等待 PLL 锁定、DDR 就绪后怎样放行数据，都需要工程中相应的控制逻辑。')
table(['方式','实际改变的内容','断电之后'],[
('下载 FPGA SRAM','立即配置 FPGA 的电路结构，适合迭代调试。','这次 SRAM 配置丢失；下次启动加载什么取决于持久存储中的映像。'),
('烧写外部 Flash','把配置映像存入指定非易失存储位置。','映像保留；启动模式、器件选择和地址正确时可再次加载。'),
('加载 RISC-V 软件','在已具备处理器系统的设计上运行处理器指令。','能否自动重启取决于软件映像、启动代码和存储配置。')
],[3.5,7,6.5])
h('与熟悉的单片机建立对应')
p('在单片机中，C 语言循环常由 CPU 反复执行。RTL 中的循环若可综合，通常描述可展开或可综合的硬件结构，并不天然表示“每循环一次消耗一个时钟”。要让一个任务分几拍完成，应明确使用寄存器、计数器或状态机。')
p('多个 always 块可以描述并行硬件；同一时钟边沿上，不同寄存器按各自输入更新。采用非阻塞赋值的时序逻辑中，右侧通常按边沿前的值求值，再更新目标寄存器，因此可以形成可预测的流水级。')
p('GW5AST 集成 AE350 硬核处理器，但点灯、UART、视频时序或乘加流水线都可以仅用 FPGA 逻辑实现。只有选用处理器系统时，才需要额外的 RISC-V 软件工具链、SDK、链接与启动配置。官方 AE350 例程状态也应单独核对，不能认为板卡带 CPU 就已提供可直接使用的操作系统。[3][4]')

page('3.2 时钟 逻辑门与寄存器')
p('“时序”至少有三种含义：任务按什么顺序执行、输出波形持续多长时间，以及信号是否满足寄存器的采样要求。前两者由计数器、状态机等功能设计规定；最后一种需要结合电路延迟和静态时序分析判断。')
h('组合逻辑负责计算 寄存器负责记忆')
p('与、或、非、与非、或非等组合逻辑根据当前输入产生输出，变化需要传播时间。寄存器则在指定时钟边沿采样输入并保存结果，直到后续有效边沿再更新。或非门满足 y = ~(a | b)，只有两个输入均为 0 时输出才为 1。')
code('发送寄存器 Q  →  LUT / 组合逻辑  →  布线  →  接收寄存器 D\n       ↑                                        ↑\n       └────────── 同一时钟的相邻有效边沿 ──────────┘')
cap('图 3  典型寄存器到寄存器的数据路径。LUT 和连线都贡献延迟；真正的时钟由专用时钟网络分配。')
p('FPGA 一般不会把每一个“或”“非”符号机械地做成一个独立门。LUT 可以直接实现一定输入规模的布尔函数；综合器也会合并表达式、消除冗余或利用专用资源。因此，源代码里的运算符数量不等于实际逻辑级数。[3]')
h('建立时间与保持时间')
p('建立时间（setup）要求数据在采样边沿到来前已稳定一段时间；保持时间（hold）要求采样之后还稳定一段时间。违例时，接收寄存器可能采到错误值或出现亚稳态，不能把它理解成“最多晚一点算完”。')
code('忽略时钟偏斜时的建立时间预算：\nTclk ≥ tCQ(max) + tlogic(max) + troute(max) + tsetup + 裕量\n忽略时钟偏斜时的保持时间条件：\ntCQ(min) + tlogic(min) + troute(min) ≥ thold')
p('tCQ 是发送寄存器从时钟到输出的延迟。真实分析还要考虑时钟偏斜、抖动、不确定度和工艺电压温度角。降低时钟频率通常增加建立时间余量，却不能自动解决同一边沿的保持时间问题。应查看实现后的路径报告，而不是仅看综合成功。[6]')
h('一个数值例子')
p('假设时钟周期 10 ns，某路径的 tCQ、逻辑、布线、建立时间和裕量分别为 0.5、5.0、2.0、0.5、1.0 ns，总计 9.0 ns，简化预算还剩 1.0 ns。若逻辑延迟增加到 7.0 ns，总计 11.0 ns，则在该预算下不满足 100 MHz。以上数值仅为教学假设，不是本板的实测参数。')

page('3.3 改变或非门能否改变时序')
p('可以影响延迟，但不能仅靠“换几个门”来可靠地控制时间。需要先明确你要改变的是逻辑功能、路径速度，还是动作之间的拍数。')
table(['所做的改变','可能产生的结果','应采用的判断方法'],[
('将或门改为或非门','首先改变真值表，即改变输出功能；延迟也可能变化。','先确认逻辑功能仍正确，再查看综合与时序结果。'),
('对等价表达式化简','可能减少逻辑级数、扇出或布线负担；也可能被综合成同一结构。','比较实现后的关键路径，不能只数 RTL 运算符。'),
('串接反相器作延时','冗余逻辑可能被优化掉；保留后延迟仍随布局、温度、电压变化。','不用普通门链实现精确计时，也不用它补救时钟问题。'),
('增加流水线寄存器','把长计算分到多拍，每拍路径变短；输出延迟增加。','调整数据和控制信号的拍数对齐，并重新分析时序。'),
('修改计数器阈值','在时钟不变时改变等待周期数和事件间隔。','用周期数乘以时钟周期计算时间。'),
('配置 PLL 或调整时钟源','改变实际时钟频率或相位，影响采样节拍。','使用合法的时钟资源，更新约束并检查全部相关路径。')
],[4.1,6.6,6.3])
h('门结构优化与流水线是两种不同改法')
p('例如要计算 y = a + b + c + d，可以研究串联求和或平衡求和的结构；综合器也可能自动优化它。若一个周期仍来不及，可以第一拍计算并保存 a+b 与 c+d，第二拍再相加。这会改变接口延迟，不能只插入寄存器而忽略 valid、使能和其他并行信号。')
p('对于每拍都能接收新输入的两级流水线，填满后仍可能每拍输出一组结果，虽然每组结果要经过两级寄存器。这就是延迟与吞吐率的区别。运算位宽也必须足够，例如四个无符号 8 位数相加，最终结果需要 10 位。')
h('三个常见误区')
p('把 SDC 周期改小，不会让晶振变快；它只提高工具必须满足的目标。Verilog 仿真中的 #10 不等于综合后硬件会等待 10 ns。用普通逻辑把 clk 与某个条件直接相与，可能制造毛刺时钟；一般的慢速业务更新应优先使用时钟使能，需要门控时使用器件支持的专用资源。')

page('3.4 用时钟周期控制一个 LED')
p('如果希望 LED 每隔 0.5 秒翻转一次，可在 50 MHz 时钟域中计满 25,000,000 个周期后翻转输出。完整亮灭周期为 1 秒，闪烁频率为 1 Hz。这样控制时间依靠“数时钟”，不依靠门传播得有多慢。')
code('等待时间 = 计数周期数 / 时钟频率\n0.5 s = 25,000,000 / 50,000,000')
p('下面是教学用的单时钟逻辑片段。假定 clk 确为 50 MHz，rst 是该时钟域内已处理好的高有效同步复位；led_state 是内部亮灭状态，最终应按板上 LED 有效电平连接端口。此片段不是完整的板级可下载工程。')
code('module blink_example (\n    input  wire clk,\n    input  wire rst,\n    output reg  led_state\n);\n    reg [24:0] count;\n    always @(posedge clk) begin\n        if (rst) begin\n            count     <= 25\'d0;\n            led_state <= 1\'b0;\n        end else if (count == 25\'d24999999) begin\n            count     <= 25\'d0;\n            led_state <= ~led_state;\n        end else begin\n            count <= count + 1\'b1;\n        end\n    end\nendmodule')
p('计数从 0 到 24,999,999，共 25,000,000 拍。25 位可表示该阈值。计数器、比较器和 LED 状态寄存器同时构成硬件：每个时钟边沿更新状态，比较逻辑在边沿之间形成下一状态。')
h('移到板卡时需要补齐什么')
p('补齐顶层端口、真实时钟源、复位处理、LED 极性及 .cst/.sdc 约束。官方 led 工程和 key_led 工程的端口与时钟组织并不完全相同，应作为完整工程分别理解，不能把一个工程的端口名与另一个工程的约束直接混用。[4]')
p('若只希望某个模块每 1 ms 更新一次，可生成持续一拍的 tick，使模块在 if (tick) 时更新，而全部寄存器仍由原时钟驱动。只有确实需要独立时钟时，才设计新的时钟域并处理跨域通信。')

page('3.5 外部信号与多时钟设计')
h('按键和跨时钟数据')
p('机械按键既可能抖动，又不与 FPGA 时钟同步。常见做法是先同步到目标时钟域，再按稳定持续的周期数消抖。复位若采用异步置位，需要对各时钟域的释放进行适当同步，避免不同寄存器在边沿附近不一致地退出复位。')
p('两个时钟域之间传递慢变化的单比特电平，常用两级同步器降低亚稳态传播风险；它不保证绝对消除亚稳态，也不能保证捕获很窄的脉冲。事件可以使用握手或专门脉冲跨域电路；多比特数据应使用握手保持、异步 FIFO 等方案，不能简单地每位各接两个寄存器就认定数据一致。')
h('真正要检查的时序信息')
p('关注主时钟与派生时钟是否完整、输入输出是否被合理约束，以及建立和保持检查的最差路径。负裕量表示对应检查未满足要求；没有报错不一定意味着约束覆盖完整。先确认功能和约束，再优化长路径、扇出、流水级或目标频率。')
p('false path 和 multicycle path 是对真实设计关系的描述，不是让报告变绿的开关。前者排除不应按普通同步关系分析的路径；后者只能用于功能上确实允许跨多拍的数据传输，并需同时考虑保持时间关系。[6]')
h('官方资料与进一步阅读')
refs=[
('[1] Sipeed Tang Mega 138K Pro Dock 板卡说明与正面图片','https://wiki.sipeed.com/hardware/zh/tang/tang-mega-138k/mega-138k-pro.html'),
('[2] Sipeed 核心板规格书 v1.0 与硬件资料','https://dl.sipeed.com/shareURL/TANG/Mega_138K_Pro/01_Specification'),
('[3] 高云 GW5AST 系列数据手册 DS1239','https://cdn.gowinsemi.com.cn/DS1239E.pdf'),
('[4] Sipeed 官方示例仓库 含 led 与 key_led','https://github.com/sipeed/TangMega-138KPro-example'),
('[5] 高云 EDA 下载与 License 申请','https://www.gowinsemi.com.cn/software/1'),
('[6] 高云时序约束手册 SUG940','https://cdn.gowinsemi.com.cn/SUG940E.pdf'),
('[7] Sipeed IDE 安装指南','https://wiki.sipeed.com/hardware/zh/tang/common-doc/get_started/install-the-ide.html'),
('[8] Sipeed 原理图与全引脚约束入口','https://dl.sipeed.com/shareURL/TANG/Mega_138K_Pro')]
for title,url in refs:
    pa=p(title+'\n'+url)
    pa.paragraph_format.space_after=Pt(5);pa.paragraph_format.line_spacing=1.0
    for r in pa.runs:r.font.size=Pt(8)
cap('图 1 版权归 Sipeed 所有；图 2、图 3 为本文教学示意。版本与在线资源以官方后续更新为准。')
out=ROOT/'output/Tang_Mega_138K_Pro_开发指南.docx'
doc.save(out)
print(out)
