#pragma once
#include <stdint.h>
#include <stddef.h>

// Diagnostic decoder: complete channel messages, running status within a
// notification, and real-time messages at message boundaries. SysEx/system
// common and truncated messages are explicitly rejected; raw capture remains.
// Running status must not be carried across BLE notifications.
template<class Emit>
bool decodeMidiPacket(const uint8_t* p, size_t n, Emit emit) {
    if (n < 3 || (p[0] & 0xc0) != 0x80 || !(p[1] & 0x80)) return false;
    size_t i = 1;
    uint8_t running = 0;
    uint16_t timestamp = uint16_t(p[0] & 0x3f) << 7;
    while (i < n) {
        if (p[i] & 0x80) {
            timestamp = (timestamp & 0x1f80) | (p[i++] & 0x7f);
            if (i == n) return false;
        }
        uint8_t status = running;
        if (p[i] & 0x80) {
            status = p[i++];
            if (status >= 0xf8) { emit(status, 0, 0, timestamp); continue; }
            if (status >= 0xf0) return false;
            running = status;
        }
        if (status < 0x80 || status >= 0xf0) return false;
        size_t count = ((status & 0xf0) == 0xc0 || (status & 0xf0) == 0xd0) ? 1 : 2;
        if (n - i < count) return false;
        uint8_t a = p[i++], b = count == 2 ? p[i++] : 0;
        if ((a | b) & 0x80) return false;
        emit(status, a, b, timestamp);
    }
    return true;
}
