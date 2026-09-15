"""Run the real firmware loop with simulated USB, pixels, and flash; no board needed."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
    work = Path(folder)
    (work / "USB").mkdir()
    (work / "USB/PluggableUSBSerial.h").write_text("#pragma once\n#define _SerialUSB Serial\n")
    (work / "Arduino.h").write_text(r'''
#pragma once
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
uint32_t clockMs = 0;
uint32_t millis() { return clockMs; }
struct SerialDevice {
    std::string input, output;
    unsigned rate = 57600, capacity = 64;
    void begin(unsigned) {}
    unsigned baud() { return rate; }
    bool available() { return !input.empty(); }
    int read() { int c = uint8_t(input[0]); input.erase(0, 1); return c; }
    void print(const char *s) {
        if (!capacity) throw std::runtime_error("firmware blocked on USB reply");
        output += s;
    }
    void println(const char *s) { print(s); print("\r\n"); }
    void send_nb(uint8_t *data, uint32_t count, uint32_t *actual) {
        *actual = std::min(count, capacity);
        output.append(reinterpret_cast<char *>(data), *actual);
    }
} Serial;
''')
    (work / "Adafruit_NeoPixel.h").write_text(r'''
#pragma once
#define NEO_GRB 0
#define NEO_KHZ800 0
struct Adafruit_NeoPixel {
    uint32_t displayed = 0, pending = 0;
    Adafruit_NeoPixel(int, int, int) {}
    void begin() {}
    void clear() { pending = 0; }
    void show() { displayed = pending; }
    void fill(uint32_t c) { pending = c; }
};
''')
    (work / "kvstore_global_api.h").write_text(r'''
#pragma once
uint8_t flash[44]{};
bool flashValid = false, failSave = false;
int writes = 0;
int kv_set(const char *, const void *data, size_t size, int) {
    if (failSave) return -1;
    memcpy(flash, data, size); flashValid = true; ++writes; return 0;
}
int kv_get(const char *, void *data, size_t size, size_t *actual) {
    if (!flashValid) return -1;
    memcpy(data, flash, size); *actual = size; return 0;
}
''')
    (work / "main.cpp").write_text(r'''
#include "Firmware.h"
#include <cassert>
#include <iostream>
void pump(int times = 100) { while (times--) { clockMs += 10; loop(); } }
int main() {
    setup();
    Serial.input = "STATUS busy\nTIMEOUT 2\n";
    pump(20);
    assert(matrix.displayed == 0xff0000);
    assert(writes == 0);
    Serial.input = "GET\n";
    Serial.capacity = 0;
    pump(300); // A stalled reader must not keep the stale busy light on.
    assert(matrix.displayed == 0);
    Serial.capacity = 7; // Exercise partial USB writes and complete reply framing.
    pump();
    assert(Serial.output.find("INFO 1\n") != std::string::npos);
    assert(Serial.output.find("PRESET offline 0 0 0 steady 1000\nOK\n") != std::string::npos);
    Serial.input = "BRIGHTNESS 64\nSAVE\n";
    pump();
    assert(writes == 1);
    notifier = statuslight::Notifier();
    setup();
    assert(notifier.snapshot().brightness == 64);
    failSave = true;
    Serial.input = "SAVE\n";
    pump();
    assert(Serial.output.find("ERR storage\n") != std::string::npos);
    Serial.rate = 115200;
    Serial.input = std::string("\xff\0\0", 3);
    pump(5);
    assert(matrix.displayed == 0x400000);
    std::cout << "firmware loop checks passed\n";
}
''')
    binary = work / "check"
    subprocess.run(["g++", "-std=c++11", "-Wall", "-Wextra", "-Werror",
                    "-DARDUINO_ARCH_MBED", "-I", str(work), "-I", str(root),
                    str(work / "main.cpp"), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
