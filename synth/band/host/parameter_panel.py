"""Live parameter monitor and editor for the 256-voice workstation."""
import time
import tkinter as tk
from tkinter import ttk

import serial
from protocol import Decoder, Event


# Label, state offset, width, accepted range, command and parameter selector.
PARAMETERS = [
    ("总音量", 1, 7, 0, 127, 10, 0),
    ("速度", 8, 8, 40, 240, 15, 0),
    ("声部表情", 117, 7, 0, 127, 11, 0),
    ("起音", 67, 14, 1, 16383, 11, 4),
    ("释音", 81, 4, 0, 15, 11, 7),
]


class ParameterPanel:
    def __init__(self, root):
        self.root = root
        root.title("星群 · 演奏参数")
        body = ttk.Frame(root, padding=18)
        body.pack(fill="both", expand=True)
        self.port = tk.StringVar(value="COM12")
        self.status = tk.StringVar(value="未连接")
        self.context = tk.StringVar(value="等待 FPGA 画面")
        self.message = tk.StringVar()
        self.link = None
        self.part = None
        self.last_frame = 0
        self.rows = []
        ttk.Entry(body, width=12, textvariable=self.port).grid(row=0, column=0)
        self.connect_button = ttk.Button(body, text="连接", command=self.toggle)
        self.connect_button.grid(row=0, column=1)
        ttk.Label(body, textvariable=self.status).grid(row=0, column=2, columnspan=2)
        ttk.Label(body, textvariable=self.context).grid(row=1, column=0, columnspan=4, pady=10)
        for col, title in enumerate(("参数", "板上读数", "目标值", "")):
            ttk.Label(body, text=title).grid(row=2, column=col, padx=8)
        for i, (name, _, _, low, high, _, _) in enumerate(PARAMETERS):
            value, target = tk.StringVar(value="—"), tk.StringVar()
            ttk.Label(body, text=name).grid(row=i+3, column=0, sticky="w")
            ttk.Label(body, textvariable=value).grid(row=i+3, column=1)
            ttk.Entry(body, width=10, textvariable=target).grid(row=i+3, column=2, pady=3)
            ttk.Button(body, text=f"写入 ({low}–{high})", command=lambda i=i: self.apply(i)).grid(row=i+3, column=3)
            self.rows.append((value, target))
        ttk.Label(body, textvariable=self.message).grid(row=8, column=0, columnspan=4, pady=8)
        root.protocol("WM_DELETE_WINDOW", self.exit)
        root.after(0, self.toggle)
        root.after(150, self.poll)

    def disconnect(self):
        if self.link:
            self.link.close()
        self.link = None
        self.part = None
        self.connect_button.configure(text="连接")
        self.context.set("等待 FPGA 画面")
        for value, _ in self.rows:
            value.set("—")

    def toggle(self):
        if self.link:
            self.disconnect()
            self.status.set("已断开")
            return
        try:
            self.link = serial.Serial(self.port.get().strip(), 1000000, timeout=0, write_timeout=.15)
            self.decoder = Decoder()
            self.last_frame = 0
            self.connect_button.configure(text="断开")
            self.status.set("等待回读")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def apply(self, i):
        if not self.link or self.part is None or time.monotonic()-self.last_frame > 1:
            self.message.set("请先连接，并等待板上读数。")
            return
        name, _, _, low, high, kind, flag = PARAMETERS[i]
        try:
            value = int(self.rows[i][1].get())
            if not low <= value <= high:
                raise ValueError
        except ValueError:
            self.message.set(f"{name}请输入 {low} 到 {high} 的整数。")
            return
        try:
            self.link.write(Event(kind, part=self.part, flags=flag, parameter=value).encode_uart())
            self.message.set(f"已发送{name} {value}，请核对板上读数。")
        except OSError as exc:
            self.disconnect()
            self.status.set(str(exc))

    def poll(self):
        try:
            if self.link:
                for raw in self.decoder.feed(self.link.read(4096)):
                    if raw[1] != 0xa4:
                        continue
                    state = int.from_bytes(raw[4:20], "little")
                    self.part = (state >> 46) & 15
                    self.last_frame = time.monotonic()
                    self.status.set("实时回读")
                    self.context.set(f"声部 {self.part:02d}   ·   "+("播放中" if state & 1 else "已停止"))
                    for (value, _), (_, bit, width, *_) in zip(self.rows, PARAMETERS):
                        value.set(str((state >> bit) & ((1 << width)-1)))
                if time.monotonic()-self.last_frame > 1:
                    self.status.set("等待 FPGA 回读")
                self.link.write(Event(20, flags=77).encode_uart())
        except OSError as exc:
            self.disconnect()
            self.status.set(str(exc))
        self.root.after(150, self.poll)

    def exit(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    ParameterPanel(root)
    root.mainloop()
