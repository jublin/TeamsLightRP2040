#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace statuslight {

enum class Result { None, Ok, Error, Get, Save };
enum Effect : uint8_t { Steady, Blink, Pulse };
struct Preset {
    uint16_t periodMs;
    uint8_t red, green, blue, effect;
};
struct Config {
    uint32_t version, timeoutMs;
    Preset presets[5];
    uint8_t brightness, reserved;
    uint32_t checksum;
};
static_assert(sizeof(Config) == 44, "Unexpected config layout");

class Notifier {
public:
    Notifier() { defaults(); }

    void setCommandMode(bool enabled) {
        if (commands_ != enabled) {
            commands_ = enabled;
            length_ = 0;
            invalid_ = false;
            notificationMs_ = 0;
        }
    }

    Result feed(uint8_t byte, uint32_t now) {
        if (!commands_) {
            if (length_ && uint32_t(now - byteAt_) >= 1000) length_ = 0;
            byteAt_ = now;
            line_[length_++] = static_cast<char>(byte);
            if (length_ == 3) {
                raw_ = {1000, uint8_t(line_[0]), uint8_t(line_[1]), uint8_t(line_[2]), Steady};
                status_ = -1;
                haveStatus_ = true;
                statusAt_ = lastSeen_ = now;
                stale_ = false;
                length_ = 0;
            }
            return Result::None;
        }
        if (byte == '\n') {
            line_[length_] = 0;
            Result result = invalid_ ? Result::Error : command(now);
            length_ = 0;
            invalid_ = false;
            return result;
        }
        if (byte == '\r') return Result::None;
        if ((byte < 32 && byte != '\t') || byte > 126 || length_ == sizeof(line_) - 1)
            invalid_ = true;
        else if (!invalid_) line_[length_++] = static_cast<char>(byte);
        return Result::None;
    }

    uint32_t color(uint32_t now) {
        if (notificationMs_ && uint32_t(now - notificationAt_) >= notificationMs_) notificationMs_ = 0;
        if (haveStatus_ && config_.timeoutMs && uint32_t(now - lastSeen_) >= config_.timeoutMs) stale_ = true;
        if (!enabled_) return 0;
        // A stale connection overrides even a still-running notification.
        const Preset *preset = nullptr;
        uint32_t start = statusAt_;
        if (stale_) {
            preset = &config_.presets[4];
            start = lastSeen_ + config_.timeoutMs;
        } else if (notificationMs_ && uint32_t(now - notificationAt_) < notificationMs_) {
            preset = &notification_;
            start = notificationAt_;
        } else if (haveStatus_) {
            preset = status_ < 0 ? &raw_ : &config_.presets[status_];
        }
        if (!preset) return 0;
        uint32_t level = 255, maximum = 255;
        uint32_t phase = uint32_t(now - start) % preset->periodMs;
        if (preset->effect == Blink) level = phase < preset->periodMs / 2 ? 255 : 0;
        if (preset->effect == Pulse) {
            uint32_t half = preset->periodMs / 2;
            level = phase <= half ? phase : preset->periodMs - phase;
            maximum = phase <= half ? half : preset->periodMs - half;
        }
        uint32_t scale = level * config_.brightness;
        uint32_t divisor = maximum * 255;
        return ((preset->red * scale / divisor) << 16) |
               ((preset->green * scale / divisor) << 8) | (preset->blue * scale / divisor);
    }

    Config snapshot() const {
        Config saved = config_;
        saved.checksum = checksum(saved);
        return saved;
    }

    bool restore(const Config &saved) {
        if (saved.version != 1 || saved.reserved != 0 || saved.timeoutMs > 86400000 ||
            saved.checksum != checksum(saved)) return false;
        for (const auto &p : saved.presets)
            if (p.effect > Pulse || p.periodMs < 100 || p.periodMs > 60000) return false;
        config_ = saved;
        return true;
    }

    void describe(char *out, size_t size, uint32_t now) const {
        int used = snprintf(out, size, "INFO 1\nBRIGHTNESS %u\nTIMEOUT %lu\nENABLED %u\nSTATUS %s\nSTALE %u\n",
            config_.brightness, static_cast<unsigned long>(config_.timeoutMs / 1000), enabled_,
            !haveStatus_ ? "none" : status_ < 0 ? "rgb" : names()[status_],
            stale_ || (haveStatus_ && config_.timeoutMs && uint32_t(now - lastSeen_) >= config_.timeoutMs));
        for (int i = 0; i < 5 && used >= 0 && size_t(used) < size; ++i) {
            const Preset &p = config_.presets[i];
            used += snprintf(out + used, size - used, "PRESET %s %u %u %u %s %u\n", names()[i],
                p.red, p.green, p.blue, effects()[p.effect], p.periodMs);
        }
    }

private:
    Config config_{};
    Preset raw_{1000, 0, 0, 0, Steady}, notification_{1000, 0, 0, 0, Steady};
    bool commands_ = false, enabled_ = true, haveStatus_ = false, invalid_ = false, stale_ = false;
    int status_ = -1;
    uint32_t statusAt_ = 0, lastSeen_ = 0, notificationAt_ = 0, notificationMs_ = 0, byteAt_ = 0;
    char line_[96]{};
    size_t length_ = 0;

    static const char *const *names() {
        static const char *const values[] = {"available", "busy", "away", "dnd", "offline"};
        return values;
    }
    static const char *const *effects() {
        static const char *const values[] = {"steady", "blink", "pulse"};
        return values;
    }
    static int index(const char *text, const char *const *values, int count) {
        for (int i = 0; i < count; ++i) if (!strcmp(text, values[i])) return i;
        return -1;
    }
    static bool number(const char *text, uint32_t max, uint32_t &value) {
        value = 0;
        if (!*text) return false;
        for (; *text; ++text) {
            if (*text < '0' || *text > '9') return false;
            uint32_t digit = *text - '0';
            if (value > max / 10 || (value == max / 10 && digit > max % 10)) return false;
            value = value * 10 + digit;
        }
        return true;
    }
    static bool parsePreset(char **args, Preset &p) {
        uint32_t r, g, b, period;
        int effect = index(args[3], effects(), 3);
        if (!number(args[0], 255, r) || !number(args[1], 255, g) || !number(args[2], 255, b) ||
            effect < 0 || !number(args[4], 60000, period) || period < 100) return false;
        p = {uint16_t(period), uint8_t(r), uint8_t(g), uint8_t(b), uint8_t(effect)};
        return true;
    }
    static uint32_t checksum(const Config &config) {
        const uint8_t *data = reinterpret_cast<const uint8_t *>(&config);
        uint32_t hash = 2166136261u;
        for (size_t i = 0; i < offsetof(Config, checksum); ++i) hash = (hash ^ data[i]) * 16777619u;
        return hash;
    }
    void defaults() {
        config_ = {};
        config_.version = 1;
        config_.brightness = 255;
        config_.presets[0] = {1000, 0, 255, 0, Steady};
        config_.presets[1] = {1000, 255, 0, 0, Steady};
        config_.presets[2] = {1000, 255, 160, 0, Steady};
        config_.presets[3] = {1000, 180, 0, 255, Steady};
        config_.presets[4] = {1000, 0, 0, 0, Steady};
        stale_ = false;
    }
    Result command(uint32_t now) {
        char *args[8], *context = nullptr;
        int count = 0;
        for (char *p = strtok_r(line_, " \t", &context); p; p = strtok_r(nullptr, " \t", &context)) {
            if (count == 8) return Result::Error;
            args[count++] = p;
        }
        if (!count) return Result::None;
        if (count == 1) {
            if (!strcmp(args[0], "GET")) return Result::Get;
            if (!strcmp(args[0], "SAVE")) return Result::Save;
            if (!strcmp(args[0], "DEFAULTS")) defaults();
            else if (!strcmp(args[0], "OFF")) enabled_ = false;
            else if (!strcmp(args[0], "ON")) enabled_ = true;
            else if (!strcmp(args[0], "PING")) { lastSeen_ = now; stale_ = false; }
            else if (!strcmp(args[0], "CLEAR")) notificationMs_ = 0;
            else return Result::Error;
            return Result::Ok;
        }
        uint32_t value;
        if (count == 2 && !strcmp(args[0], "STATUS")) {
            int selected = index(args[1], names(), 5);
            if (selected < 0) return Result::Error;
            status_ = selected;
            haveStatus_ = true;
            statusAt_ = lastSeen_ = now;
            stale_ = false;
        } else if (count == 2 && !strcmp(args[0], "BRIGHTNESS") && number(args[1], 255, value)) {
            config_.brightness = uint8_t(value);
        } else if (count == 2 && !strcmp(args[0], "TIMEOUT") && number(args[1], 86400, value)) {
            config_.timeoutMs = value * 1000;
            stale_ = false;
        } else if (count == 7 && !strcmp(args[0], "PRESET")) {
            int selected = index(args[1], names(), 5);
            Preset p;
            if (selected < 0 || !parsePreset(args + 2, p)) return Result::Error;
            config_.presets[selected] = p;
        } else if (count == 7 && !strcmp(args[0], "NOTIFY")) {
            Preset p;
            if (!parsePreset(args + 1, p) || !number(args[6], 600000, value) || !value) return Result::Error;
            notification_ = p;
            notificationAt_ = now;
            notificationMs_ = value;
        } else return Result::Error;
        return Result::Ok;
    }
};

} // namespace statuslight
