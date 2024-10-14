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

Adafruit_NeoPixel matrix(LED_COUNT, LED_PIN, NEO_GRB );


char rgb[3];


// put function declarations here:
int myFunction(int, int);

void setup() {

  Serial.begin(9600);

  // put your setup code here, to run once:

  matrix.begin();           // INITIALIZE NeoPixel matrix object (REQUIRED)
  matrix.show();            // Turn OFF all pixels ASAP
  matrix.setBrightness(120); // Set BRIGHTNESS to about 1/5 (max = 255)
}

// loop() function -- runs repeatedly as long as board is on ---------------
void loop() {

  uint32_t color;
  Serial.readBytes(rgb, 3);
  color = matrix.Color(rgb[0],rgb[1],rgb[2]);
  for(int i = 0; i < LED_COUNT; i++){
    matrix.setPixelColor(i, color);
  }
  matrix.show();
  
  
}