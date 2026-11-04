// Four local seats use sources 17..20, distinct from USB/MIDI host seats 1..4.
// Contacts 0..15 lead; 16..31 drums; 32..47 harmony; 48..63 choir.
// Each release retains the part/epoch/note identity captured at its accepted onset.
module local_performer(
 input wire clk,rst,panic,pad_valid,output wire pad_ready,input wire pad_off,
 input wire [6:0] pad_contact,pad_pressure,input wire [31:0] pad_serial,
 input wire [3:0] root,input wire minor_mode,
 output wire busy,output reg [3:0] status_part,input wire status_valid,
 input wire [7:0] status_owner,input wire [31:0] status_epoch,
 output wire command_valid,input wire command_ready,output wire [1:0] command,
 output wire [3:0] command_part,output wire [7:0] command_source,
 output wire manual_valid,input wire manual_ready,output wire [1:0] manual_kind,
 output reg [7:0] manual_source,manual_contact,output reg [3:0] manual_part,
 output reg [31:0] manual_epoch,manual_serial,output reg [6:0] manual_note,manual_velocity,
 output reg [31:0] denied,output reg [63:0] held_contacts
);
 reg [2:0] state;reg [5:0] contact;reg off;reg [9:0] takeover_wait;
 reg [31:0] epochs[0:63],serials[0:63];reg [3:0] parts[0:63];reg [6:0] notes[0:63];
 reg other_held;integer h;
 always @*begin other_held=0;for(h=0;h<64;h=h+1)if(h!=contact&&held_contacts[h]&&parts[h]==manual_part)other_held=1;end
 function [3:0] scale;input [2:0] index;input minor_key;
 begin case(index)0:scale=0;1:scale=2;2:scale=minor_key?3:4;3:scale=5;4:scale=7;5:scale=minor_key?8:9;6:scale=minor_key?10:11;7:scale=12;endcase end endfunction
 wire [1:0] seat=pad_contact[5:4];
 wire [3:0] mapped_part=seat==0?6:seat==1?(pad_contact[3:0]%3):seat==2?4:7;
 wire [6:0] mapped_note=seat==1?(mapped_part==0?36:mapped_part==1?38:42):
  (seat==0?60:48)+root+scale(pad_contact[2:0],minor_mode)+(pad_contact[3]?12:0);
 assign pad_ready=state==0&&!rst&&!panic;
 assign busy=state!=0;assign command_valid=state==2||state==5;
 assign command=state==5?2'd1:2'd0;assign command_part=status_part;assign command_source=manual_source;
 assign manual_valid=state==4;assign manual_kind=off?2'd1:2'd0;
 always @(posedge clk)begin
  if(rst||panic)begin state<=0;held_contacts<=0;denied<=0;status_part<=0;takeover_wait<=0;end
  else case(state)
   0:if(pad_valid)begin
    if(pad_contact>=64)begin denied<=denied+1'b1;end
    else begin
     contact<=pad_contact[5:0];off<=pad_off;manual_source<=17+seat;manual_contact<={2'd0,pad_contact[5:0]};manual_serial<=pad_serial;
     if(pad_off)begin
      if(held_contacts[pad_contact[5:0]]&&serials[pad_contact[5:0]]==pad_serial)begin
       status_part<=parts[pad_contact[5:0]];manual_part<=parts[pad_contact[5:0]];manual_note<=notes[pad_contact[5:0]];manual_epoch<=epochs[pad_contact[5:0]];manual_velocity<=0;state<=4;
      end
     end else begin
      status_part<=mapped_part;manual_part<=mapped_part;manual_note<=mapped_note;manual_velocity<=pad_pressure==0?1:pad_pressure;state<=1;
     end
    end
   end
   1:if(status_valid)begin
    if(status_owner==manual_source||status_owner==0)state<=2;
    else begin denied<=denied+1'b1;state<=0;end
   end
   2:if(command_ready)begin state<=3;takeover_wait<=0;end
   3:begin
    takeover_wait<=takeover_wait+1'b1;
    if(status_valid&&status_owner==manual_source)begin manual_epoch<=status_epoch;state<=4;end
    else if((&takeover_wait)||(status_valid&&status_owner!=0))begin denied<=denied+1'b1;state<=0;end
   end
   4:if(manual_ready)begin
    held_contacts[contact]<=!off;
    if(!off)begin epochs[contact]<=manual_epoch;serials[contact]<=manual_serial;parts[contact]<=manual_part;notes[contact]<=manual_note;end
    state<=off&&!other_held?5:0;
   end
   5:if(command_ready)state<=0;
   default:state<=0;
  endcase
 end
endmodule
