#pragma once

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "StatusLight.h"

#if defined(ARDUINO_ARCH_MBED)
#include <kvstore_global_api.h>
#include <USB/PluggableUSBSerial.h>
#else
#include <EEPROM.h>
#include <tusb.h>
#endif

#ifndef LED_PIN
#define LED_PIN 15
#endif
#ifndef LED_COUNT
#define LED_COUNT 16
#endif

statuslight::Notifier notifier;
Adafruit_NeoPixel matrix(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

bool saveSettings() {
    const statuslight::Config saved = notifier.snapshot();
#if defined(ARDUINO_ARCH_MBED)
    return kv_set("/kv/statuslight", &saved, sizeof saved, 0) == 0;
#else
    EEPROM.put(0, saved);
    return EEPROM.commit();
#endif
}

void setup() {
    matrix.begin();
    matrix.clear();
    matrix.show();
    Serial.begin(115200);
    statuslight::Config saved{};
#if defined(ARDUINO_ARCH_MBED)
    size_t actual = 0;
    if (kv_get("/kv/statuslight", &saved, sizeof saved, &actual) == 0 && actual == sizeof saved)
        notifier.restore(saved);
#else
    EEPROM.begin(256);
    EEPROM.get(0, saved);
    notifier.restore(saved);
#endif
}

void loop() {
    static char reply[512];
    static uint32_t replySize = 0, sent = 0;
    static bool previousMode = false;
    // USB baud selects the protocol; 1200 is reserved for flashing.
#if defined(ARDUINO_ARCH_MBED)
    bool commandMode = Serial.baud() == 57600;
#else
    cdc_line_coding_t coding;
    tud_cdc_get_line_coding(&coding);
    bool commandMode = coding.bit_rate == 57600;
#endif
    if (commandMode != previousMode) replySize = sent = 0;
    previousMode = commandMode;
    notifier.setCommandMode(commandMode);
    // Bound each batch so serial floods cannot starve animation and timeout checks.
    for (int i = 0; i < 64 && !replySize && Serial.available(); ++i) {
        statuslight::Result result = notifier.feed(uint8_t(Serial.read()), millis());
        switch (result) {
        case statuslight::Result::Save:
            strcpy(reply, saveSettings() ? "OK\n" : "ERR storage\n");
            break;
        case statuslight::Result::Get:
            notifier.describe(reply, sizeof(reply) - 4, millis());
            strcat(reply, "OK\n");
            break;
        case statuslight::Result::Ok: strcpy(reply, "OK\n"); break;
        case statuslight::Result::Error: strcpy(reply, "ERR command\n"); break;
        case statuslight::Result::None: continue;
        }
        replySize = strlen(reply);
    }
    // Keep one reply in flight; a host that stops reading must not freeze the light.
    if (replySize) {
        uint32_t written = 0;
#if defined(ARDUINO_ARCH_MBED)
        _SerialUSB.send_nb(reinterpret_cast<uint8_t *>(reply + sent), replySize - sent, &written);
#else
        int available = Serial.availableForWrite();
        if (available > 0) {
            uint32_t count = replySize - sent;
            if (count > uint32_t(available)) count = uint32_t(available);
            written = Serial.write(reinterpret_cast<uint8_t *>(reply + sent), count);
        }
#endif
        sent += written;
        if (sent == replySize) replySize = sent = 0;
    }
    static uint32_t lastFrame = 0, previousColor = 0;
    uint32_t now = millis();
    if (uint32_t(now - lastFrame) < 10) return;
    lastFrame = now;
    uint32_t color = notifier.color(now);
    if (color != previousColor) {
        matrix.fill(color);
        matrix.show();
        previousColor = color;
    }
}
