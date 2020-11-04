'''import spidev
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)'''

from PIL import Image, ImageDraw

import io
import numpy
import time

import asyncio
#from threading import Thread

import cv2

class Screen:
    def __init__(self, width, height):
        ## Display ##
        self.display = None
        self.BUFFER_LEN = 50
        self.BAUDRATE = 40000000
        self.DRAW_SLEEP = 0.0000001
        self.stopStream = False
        self.pauseStream = False

        ## Dimensions ##
        self.width = width
        self.height = height

        ## Interfaces ##
        self.spi = None

        ## Frames ##
        self.frames = []

        self.cv_window_name = 'frame'

        self.init_screen()
    
    def init_screen(self):
        
        cv2.namedWindow(self.cv_window_name, cv2.WINDOW_FREERATIO)
        cv2.setWindowProperty(self.cv_window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        img = Image.new("RGB",(self.width,self.height))
        img.paste((0,0,0),[0,0,self.width,self.height])
        frame = numpy.array(img)
        cv2.imshow(self.cv_window_name, frame)
        if(cv2.waitKey(100) & 0xFF == ord('e')):
            pass
    
    ### if you want to use the ili9341 as an external SPI display
    '''def init_screen(self):
        import adafruit_rgb_display.ili9341 as ili9341

        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = digitalio.DigitalInOut(board.D24)

        # Setup SPI bus using hardware SPI:
        self.spi = board.SPI()

        self.display = ili9341.ILI9341(
            self.spi,
            rotation=90,  # 2.2", 2.4", 2.8", 3.2" ILI9341
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=self.BAUDRATE,
        )'''
        '''from ili9341 import TFT24T

        # Create TFT LCD/TOUCH object:
        self.display = TFT24T(spidev.SpiDev(), GPIO, landscape=False)

        # Initialize display.
        DC = 25
        RST = 24
        self.display.initLCD(DC, RST)

    async def image_to_data(self, image):
        """Generator function to convert a PIL image to 16-bit 565 RGB bytes."""
        # NumPy is much faster at doing this. NumPy code provided by:
        # Keith (https://www.blogger.com/profile/02555547344016007163)
        data = numpy.array(image.convert("RGB")).astype("uint16")
        color = (
            ((data[:, :, 0] & 0xF8) << 8)
            | ((data[:, :, 1] & 0xFC) << 3)
            | (data[:, :, 2] >> 3)
        )
        return numpy.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()'''

    async def draw_stream(self):
        print("starting drawing buffer...")
        x=0
        y=0

        while len(self.frames) < 50:
            await asyncio.sleep(0.01)
        
        i=0
        while not self.stopStream:
            #print(len(self.frames))
            t = time.time()
            if len(self.frames) > 0 and not self.pauseStream:
                pixels = self.frames[0]
                cv2.imshow(self.cv_window_name, frame)
                if(cv2.waitKey(1) & 0xFF == ord('e')):
                    pass
                self.frames.pop(0)
            
            delta = time.time() - t
            print("tot", delta,  1/delta)
            if i == 20:
                i=0
                await asyncio.sleep(0.5)
            i+=1
    
    async def recv_frame(self, frame):
        #print("recv_frame")
        #print(len(frame))
        if len(frame) > 1:
            img = Image.open(io.BytesIO(frame))
            pixels = numpy.array(img)
            self.frames.append(pixels)
        else:
            #print('pause!', frame)
            self.pauseStream = True
        await asyncio.sleep(0.01)

    def setDisplay(self, frame):
        img = Image.open(io.BytesIO(frame))
        frame = numpy.array(img)
        cv2.imshow(self.cv_window_name, frame)
        if(cv2.waitKey(1) & 0xFF == ord('e')):
            pass
