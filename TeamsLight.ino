#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

#define LED_PIN    15
#define GROUND_PIN 13
#define LED_COUNT 16

//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_RGBW    Pixels are wired for RGBW bitstream (NeoPixel RGBW products)

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB );

unsigned long pixelPrevious = 0;        // Previous Pixel Millis
unsigned long patternPrevious = 0;      // Previous Pattern Millis
int           patternCurrent = 0;       // Current Pattern Number
int           patternInterval = 5000;   // Pattern Interval (ms)
bool          patternComplete = false;

int           pixelInterval = 50;       // Pixel Interval (ms)
int           pixelQueue = 0;           // Pattern Pixel Queue
int           pixelCycle = 0;           // Pattern Pixel Cycle
uint16_t      pixelNumber = LED_COUNT;  // Total Number of Pixels

void theaterChaseRainbow(uint8_t wait);
void colorWipe(uint32_t color, int wait);
void rainbow(uint8_t wait);
uint32_t Wheel(byte WheelPos);
void theaterChase(uint32_t color, int wait);

char rgb[3];
byte r,g,b;

// put function declarations here:
int myFunction(int, int);

void setup() {

  Serial.begin(9600);

  // put your setup code here, to run once:

  strip.begin();           // INITIALIZE NeoPixel strip object (REQUIRED)
  strip.show();            // Turn OFF all pixels ASAP
  strip.setBrightness(122000); // Set BRIGHTNESS to about 1/5 (max = 255)
}

// loop() function -- runs repeatedly as long as board is on ---------------
void loop() {

  uint32_t color;
  Serial.readBytes(rgb, 3);
  color = strip.Color(rgb[0],rgb[1],rgb[2]);
  for(int i = 0; i < LED_COUNT; i++){
    strip.setPixelColor(i, color);
  }
  strip.show();
  
  
}