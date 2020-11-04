from xpt2046 import Touch
from gpiozero import Button, DigitalOutputDevice
import board
import busio
import asyncio

class TouchScreen:
    def __init__(self):
        cs = DigitalOutputDevice(17)
        clk = board.SCLK_1	# same as writing 21
        mosi = board.MOSI_1	# same as writing 20
        miso = board.MISO_1	# same as writing 19
        irq = Button(26)

        spi = busio.SPI(clk, mosi, miso)	# auxiliary SPI

        self.xpt = Touch(spi, cs=cs, int_pin=irq, int_handler=self.__touchscreen_press)

        self.x = 0
        self.y = 0
    
    def __touchscreen_press(self, x, y):
        print("touch", x, y)
        self.x = x
        self.y = y
    
    async def listen_touch(self):
        while True:
            raw_t = self.xpt.raw_touch()
            if raw_t is not None:
                raw_x = raw_t[0]
                raw_y = raw_t[1]
                self.x, self.y = self.xpt.normalize(raw_x, raw_y)
            else:
                self.x = 0
                self.y = 0
            await asyncio.sleep(0.5)
    
    def get_touch_coords(self):
        return self.x, self.y