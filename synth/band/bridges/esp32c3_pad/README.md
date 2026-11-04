# SMC-PAD POCKET / ESP32-C3 MIDI receiver and color configuration

This is a separate firmware from `../esp32c3` (phone control server).
It actively scans for SMC/PAD-named BLE devices, verifies the standard BLE MIDI
service, and subscribes to MIDI notifications. Version 3 also subscribes to the
vendor AE42 replies and offers bounded read/query/color commands on USB Serial.
It does not implement a phone
server or transmit to FPGA UART. GPIO4/5 are not configured by this program.

USB Serial/JTAG CDC is enabled. No deep sleep or USB pin reassignment is used.
The original C3 Flash is backed up under
`synth/band/evidence/c3_pad_bringup_20261031/original_flash.bin`.

## Build

```powershell
$env:PYTHONPATH='D:\StarclusterBuilds\python_tools'
$env:PLATFORMIO_CORE_DIR='D:\StarclusterBuilds\platformio'
python -m platformio run -d synth/band/bridges/esp32c3_pad
```

## Verification

1. Keep only C3 USB attached. Power up the pad and release any other BLE connection.
2. Expect `READY BLE_MIDI_SUBSCRIBED` then increasing uptime in `STATUS`.
3. Press/release each pad with different force; retain `RAW` and `MIDI` records.
4. Check note on/off (including velocity-zero note on), pressure and multi-pad events.
5. Check `dropped=0`, `unsupported=0`, and `active=0` after all pads are released.
6. Turn the pad off/on to verify connection loss and resubscription.

The diagnostic parser handles complete channel messages and packet-local running
status. SysEx, system common and fragmented channel messages are outside its scope
and explicitly reported; all raw payloads remain in the capture. Timestamp rollover
is not used for performance measurement. USB log timing is not audio latency.
The queue is bounded and loss is counted. This diagnostic is not yet a performance
bridge; disconnect handling only clears its local held-note display.

Hardware pairing, actual MIDI behavior and FPGA integration must be reported
separately from compile/parser-test success.

## Observed hardware result (2026-10-31)

- C3 rev0.4, 4 MB Flash, COM8: original Flash backed up; new image written with
  hash verification. A physical RESET was needed to leave download mode.
- Connected to the pad and subscribed to its BLE MIDI characteristic.
- Device counters reached 54 received / 54 decoded, 0 queue drops, 0 unsupported
  packets; held-note count returned to zero. This is not proof of zero RF loss.
- The continuous detailed capture contains eight note-on/off pairs for notes
  20..27 on MIDI channel 10, velocities 44..50, plus 24 channel-pressure messages.
  Initial 14 events were counted but not fully captured during monitor handoff.
- User reported exercising all 16 pads; only eight distinct note numbers were
  captured. Remaining pad modes/mappings are unresolved; do not claim 16-pad pass.
- The observed pressure is channel pressure (0xD9), not polyphonic per-note pressure.
- Reconnection recovery, phone concurrency, full mapping and FPGA/audio have not
  been verified. Detailed evidence: `evidence/c3_pad_bringup_20261031/result.json`.

## Pocket_004 color configuration verified on real hardware

Evidence folder: `synth/band/evidence/c3_color_20261031/`.
The query reply identifies this unit as `SMC-PAD Pocket_004`. The layout below
was established by reading its own configuration, not by reusing SMC-PAD offsets.

- Service AE40, command characteristic AE41, reply characteristic AE42.
- Logical packet: `00 59 command lengthLE24 payload checksum`;
  `checksum=(~sum(payload)) & 255`. GATT responses may be fragmented.
- `query`: command 0x11, empty payload.
- `read REGION ADDRESS LENGTH`: command 0x23, payload region + addressLE32 + lengthLE24.
  CLI allows regions 4/5 and bounded 1..1000-byte reads.
- Four configuration profiles in region 5: stride 2931 bytes. Each starts with
  112 pad records of 26 bytes. RGB is at record offset 5. Notes are configurable;
  do NOT assume the note number always equals the slot index plus four.
- `color PROFILE SLOT R G B`: PROFILE 0..3, SLOT 0..111, RGB 0..255;
  command 0x22 writes only 3 bytes in region 5 at
  `PROFILE*2931 + SLOT*26 + 5`.
- These are configuration writes, not a separately established transient LED
  animation API. Reboot persistence and high-rate animation are not tested.
- Before a write, query the model, back up the relevant profile/config, read
  the target record, and verify its channel/note/color. These offsets are only
  established for the tested Pocket_004 layout. No commands run automatically.

Verified demonstration: `color 3 20 0 0 250` changed the fourth profile's slot20
(configured note24, channel10) from red FA0000 to blue 0000FA at offset9318.
Response: `00590001000000FF`. Full 11724-byte config readback differed only at
offset9318 (250->0) and offset9320 (0->250). The user confirmed one pad turned blue.
The blue setting is intentionally retained. Restore that one color with
`color 3 20 250 0 0`, after verifying the same device/layout/record.

Configuration backup and checked readback are in `prewrite_confirm.bin` and
`after_color.bin`; `config_read.py` captures and validates read responses.

The standard SMC-PAD research was useful for packet framing, but its pad base
and profile stride are different and must not be applied to this Pocket unit:
https://github.com/spectalive/smc-pad

References:
- https://manualf.oss-cn-hongkong.aliyuncs.com/manual/MIDI-KEYBOARD/SMC-PAD-POCKET.pdf
- https://docs.espressif.com/projects/esp-iot-solution/en/latest/bluetooth/ble_midi.html
- NimBLE-Arduino 1.4.2 bundled `examples/NimBLE_Client`.

## Phone control v4 (2026-10-31)

Current flashed firmware advertises `Starcluster-Control` while keeping the
BLE MIDI/configuration connection to the pad. FPGA output is still disabled.
The separate page `../phone/pad-control.html` controls only the verified demo
target (profile3, slot20, address9318), with red/blue/custom RGB and activity status.
The existing `phone/index.html` is the separate FPGA performance UI.

Service UUID: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`.
Write characteristic replaces c201 with c202; read/notify status uses c203.
Request is 8 bytes: `53 01 requestId 01 R G B checksum`, checksum is one's
complement of the sum of the preceding seven bytes. No fragmented requests.
Each valid request queries model Pocket_004, writes three RGB bytes, waits for
device acknowledgement, and reads back the same address/length/RGB.
Serial configuration commands are disabled while a phone is connected or a
phone transaction is running. No automatic write retries.

Status is 20 bytes: magic/version, padConnected, configReady, requestId,
result, R/G/B, latest MIDI status/data1/data2, decodedCount LE32, dropped LE32.
Results: 0 idle, 1 busy, 2 verified, 3 not ready, 4 wrong model, 5 write/device
failure, 6 malformed/mismatching readback, 7 timeout/disconnected (outcome unknown).
Latest MIDI is a sampled display, not a complete phone-side MIDI recorder.
This is a local bench prototype without BLE pairing/authentication; anyone nearby
using this service can change the fixed demo pad. Add access control before deployment.

Compiled and flashed v4 with hash verification. `phone_ble_test.py` used actual
Windows BLE as the phone-role central, rejecting a bad checksum, writing the
existing blue value, validating readback, and disconnecting/reconnecting while
the pad link remained connected. Full 11724-byte config comparison was unchanged.
Evidence: `../../evidence/c3_phone_20261031/`. Android actual-device test pending.

Local Android development: serve `../phone` on computer loopback port8765,
enable USB debugging on the phone and authorize the computer, then use
`adb -s DEVICE_SERIAL reverse tcp:8765 tcp:8765`. Open
`http://localhost:8765/pad-control.html` in Android Chrome and choose
Starcluster-Control in the page's Bluetooth picker. USB carries the development
page; control commands go over BLE. Keep USB connected for page reloads.
For fully wireless distribution, host the same static page on HTTPS.

## Native Android / C3 v5 update

The current flashed image is `c3-pad-phone-v5-app`. It retains v4 RGB/status
compatibility and adds KIND2 single-note mapping transactions and c204 per-event
MIDI notifications. See `../android/README.md` for the protocol and native APK.
The user confirmed on a real vivo X200 Pro that the app connects, changes the
demo pad color, and receives increasing recording event counts. Serial capture
observed 42 MIDI events with zero queue drops, zero unsupported packets, and
zero held notes at the last status. This is not an audio recording or FPGA
performance acceptance. Evidence: `../../evidence/android_app_20261031/`.

## Phone UART v6 update

Current development image `c3-pad-phone-v6-uart` additionally enables UART1:
GPIO4 TX, GPIO5 RX, 1Mbps 8N1. New c205/c206 GATT characteristics forward
CRC-checked source3 commands and FPGA replies. The queue is bounded, every
outbound frame has64 guard bytes, and disconnect/timeout/overflow releases
the phone seat. It does not yet forward the physical pad's MIDI events into
FPGA note commands. Android0.2's touch-performance page is the current control
source. FPGA candidate and actual board-test evidence are tracked separately
under `../../evidence/phone_fpga_20261031/`.
