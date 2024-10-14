# Teams Status Light - Firmware and 3D Models

Here is the code for the TeamsStatusLight python script located [Here](https://github.com/jublin/TeamsStatusLight/tree/rp2040-simple-serial)

The LED Matrix I have used can be found on [AliExpress](https://www.aliexpress.us/item/3256806834627585.html) (No affiliate link)

I used this RPi2040 Pico-Zero, also on [AliExpress](https://www.aliexpress.us/item/3256804095235134.html)

Feel free to modify as you wish. F360/Step Files will be included. 

## Flashing

For PlatformIO, the driver for the board must be loaded using [ZaDig](https://zadig.akeo.ie/]) (see [this GitHub isue](https://github.com/platformio/platform-raspberrypi/issues/2#issuecomment-828586398)).

I've copied the file contents to an Arduino Sketch as well. To use the board in Arduino - see the instructions [here](https://www.waveshare.com/wiki/RP2040-Zero)

You will need to add the board package list to Arduino package manager: https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json