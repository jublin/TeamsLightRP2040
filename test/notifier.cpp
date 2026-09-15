#include "../StatusLight.h"
#include <cassert>
#include <cstring>
#include <cstdio>

using namespace statuslight;
static Result send(Notifier &n, const char *s, uint32_t now = 0) {
    Result result = Result::None;
    while (*s) result = n.feed(static_cast<uint8_t>(*s++), now);
    return result;
}
int main() {
    Notifier n;
    assert(n.color(0) == 0);
    n.feed(255, 0); n.feed(0, 1);
    assert(n.color(1) == 0); // Partial RGB must never reach the LEDs.
    n.feed(128, 2);
    assert(n.color(2) == 0xff0080);
    n.feed(12, 3);
    n.feed(0, 1004); n.feed(255, 1004); n.feed(0, 1004);
    assert(n.color(1004) == 0x00ff00); // Expire abandoned packets.
    n.setCommandMode(true);
    assert(send(n, "PRESET busy 12 34 56 steady 1000\n") == Result::Ok);
    assert(send(n, "STATUS busy\r\n", 10) == Result::Ok);
    assert(n.color(10) == 0x0c2238);
    assert(send(n, "PRESET busy 999 0 0 steady 1000\n") == Result::Error);
    assert(send(n, "BRIGHTNESS -1\n") == Result::Error);
    assert(send(n, "BRIGHTNESS 12 junk\n") == Result::Error);
    assert(send(n, "BRIGHTNESS 128\n") == Result::Ok);
    assert(n.color(10) == 0x06111c);
    send(n, "BRIGHTNESS 255\n");
    assert(send(n, "NOTIFY 255 0 0 blink 1000 2000\n", 100) == Result::Ok);
    assert(n.color(100) == 0xff0000);
    assert(n.color(600) == 0);
    assert(n.color(2100) == 0x0c2238);
    send(n, "OFF\n"); assert(n.color(2100) == 0);
    send(n, "ON\n"); assert(n.color(2100) == 0x0c2238);
    send(n, "PRESET busy 100 0 0 pulse 1000\n");
    send(n, "STATUS busy\n", 3000);
    assert(n.color(3000) == 0);
    assert(n.color(3500) == 0x640000);
    assert(n.color(3750) == 0x320000);
    send(n, "TIMEOUT 2\n", 3000);
    assert(n.color(5000) == 0); // Offline default is dark.
    send(n, "PING\n", 5500);
    assert(n.color(5500) == 0x640000);
    send(n, "STATUS busy\n", 0xffffff00u);
    send(n, "NOTIFY 0 0 255 steady 1000 500\n", 0xffffff00u);
    assert(n.color(0x50) == 0x0000ff);
    assert(n.color(0xf4) == 0x640000); // Notification expiry across millis wrap.
    assert(send(n, "SAVE\n") == Result::Save);
    Config saved = n.snapshot();
    Notifier restored;
    assert(restored.restore(saved));
    restored.setCommandMode(true);
    send(restored, "STATUS busy\n", 0);
    assert(restored.color(500) == 0x640000);
    saved.presets[0].red ^= 1;
    assert(!restored.restore(saved));
    char description[512];
    restored.describe(description, sizeof description, 500);
    assert(strstr(description, "busy 100 0 0 pulse 1000"));
    assert(strstr(description, "TIMEOUT 2"));
    assert(send(n, "DEFAULTS\n") == Result::Ok);
    assert(n.snapshot().timeoutMs == 0);
    for (int i = 0; i < 110; ++i) n.feed('x', 0);
    assert(send(n, "\n") == Result::Error);
    assert(send(n, "STATUS away\n") == Result::Ok);
    assert(send(n, "STATUS away extra\n") == Result::Error);
    n.feed('O', 0); n.feed(0, 0);
    assert(send(n, "FF\n") == Result::Error); // Reject embedded NUL.
    assert(send(n, "STATUS unknown\n") == Result::Error);
    assert(send(n, "TIMEOUT 999999999999999999999\n") == Result::Error);
    n.feed('O', 0); n.setCommandMode(false);
    n.feed(10, 1); n.feed(20, 1); n.feed(30, 1);
    assert(n.color(1) == 0x0a141e);
    puts("notifier checks passed");
}
