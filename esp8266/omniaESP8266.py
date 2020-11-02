# firmware v 0.6.1
from machine import Pin, I2C, PWM, ADC
import neopixel
import framebuf
import struct
import uasyncio
import micropython

### Images ###
ONE_BIT_IMAGE = 'S'
RGBA_IMAGE = 'd'
### --- ###

### Displays ###
ONE_BIT_DISPLAY = 'D'
TOUCHSCREEN = 't'
### --- ###

### Video ###
START_STOP_VIDEO_STREAM = 'V'
VIDEO_FRAME = 'v'
### --- ###

### Audio ###
SET_AUDIO = 'A'
AUDIO_CHUNK = 'a'
### --- ###

### IO pins ###
INPUT_PIN = 'I'
REMOVE_INPUT_PIN = 'R'
OUTPUT_PIN = 'O'
PWM_PIN = 'P'
NEOPIXEL_PIN = 'N'

READ_ADC = 'e'
SET_I2C = 'i'
READ_I2C = 'c'
### --- ###

### Connectivity ###
READ_BLE = 'b'
SET_NFC = 'n'
READ_NFC = 'f'
### --- ###

### Latency ###
LATENCY = 'l'
### --- ###

class OmniaESP8266:

    def __init__(self, socket):

        self.loop = uasyncio.get_event_loop()

        self.reader = uasyncio.StreamReader(socket)
        self.writer = uasyncio.StreamWriter(socket, {})

        self.pin_in = []
        
        self.i2c = None
        self.i2c_address = None
        self.i2c_nbytes = None
        
        self.adc_pin = None

        self.nfc_reader = None

        self.oled = None
        self.oled_width = 0
        self.oled_height = 0

        self.message_types = []

        self.stream_types = [ONE_BIT_IMAGE, LATENCY]
        
        micropython.mem_info()  # log RAM info

    async def __recv_msg(self):
        # Read message length and unpack it into an integer
        raw_msglen = await self.__recvall(4)
        if not raw_msglen:
            return b'00'
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Read the message data
        return await self.__recvall(msglen)

    async def __recvall(self, n):
        # Helper function to recv n bytes or return None if EOF is hit
        data = bytearray()
        while len(data) < n:
            try:
                #sock.setblocking(False)
                packet = await self.reader.read(n - len(data))
                '''if not packet:
                    return None'''
                data.extend(packet)
            except:
                pass
        return data
    
    def addMsgType(self, msg_type):
        if not (msg_type in self.message_types):
            self.message_types.append(msg_type)
    
    def removeMsgType(self, msg_type):
        if msg_type in self.message_types:
            self.message_types.pop(self.message_types.index(msg_type))

    def run(self):
        
        recv_task = self.loop.create_task(self.__recv())
        send_task = self.loop.create_task(self.__send())
        
        self.loop.run_forever()
        
    async def __recv(self):
        
        while True:
            s = bytes(await self.__recv_msg())
            
            msg_type = chr(s[0])
            print(msg_type)
            
            msg = None
            args = []

            if not (msg_type in self.stream_types):
                msg = s.decode()[1:]
                args = list(map(int, msg.split("-")))
                print(args)
            else:
                msg = s[1:]
            
            ### message cases ###

            if(msg_type == LATENCY):
                self.latency = msg
                self.addMsgType(msg_type)

            elif(msg_type == READ_NFC): # read NFC
                flag = args[0]
                
                if flag:
                    self.addMsgType(msg_type)
                else:
                    self.removeMsgType(msg_type)
            
            elif(msg_type == INPUT_PIN): # set Input Pin
                pin = args[0]
                if( not ( pin in self.pin_in)):
                    self.pin_in.append(pin)
                self.addMsgType(msg_type)
    
            elif(msg_type == OUTPUT_PIN): # set Output Pin
                pin = args[0]
                value = args[1]
                Pin(pin, Pin.OUT).value(value)

            elif(msg_type == READ_ADC): # read ADC
                flag = args[0]

                if flag:
                    pin = args[1]
                    if not pin in self.pin_in:
                        self.adc_pin = args[1]
                    
                    self.addMsgType(msg_type)
                else:
                    self.adc_pin = None
                    self.removeMsgType(msg_type)
            
            elif(msg_type == SET_I2C): # set I2C
                sda_pin = args[0]
                scl_pin = args[1]
                
                self.i2c = I2C(-1, scl=Pin(scl_pin), sda=Pin(sda_pin))
                
            elif(msg_type == READ_I2C): # read I2C
                flag = args[0]
                
                if flag:
                    addr = args[1]
                    nbytes = args[2]
                    self.i2c_address = addr
                    self.i2c_nbytes = nbytes
                    print(send_type, isqc)
                    self.addMsgType(msg_type)
                else:
                    self.removeMsgType(msg_type)
                
            elif(msg_type == PWM_PIN): # set PWM
                pin = args[0]
                freq = args[1]
                duty = args[2]
                
                PWM(Pin(pin), freq=freq, duty=duty)
                        
            elif(msg_type == SET_NFC): # set NFC
                sclk = args[0]
                mosi = args[1]
                miso = args[2]
                rst = args[3]
                sda = args[4]
                
                from mfrc522 import MFRC522
                self.nfc_reader = MFRC522(sclk, mosi,miso,rst,sda)
            
            elif(msg_type == NEOPIXEL_PIN): # set Neopixel
                pin = args[0]
                red = args[1]
                green = args[2]
                blue = args[3]

                np = neopixel.NeoPixel(Pin(pin), 1)
                np[0]=[red,green,blue]
                np.write()
            
            elif(msg_type == ONE_BIT_DISPLAY): #set Display
                sda = args[0]
                scl = args[1]
                self.oled_width = args[2]
                self.oled_height = args[3]
                
                disp = args[4]
                
                i2c = I2C(-1, scl=Pin(scl), sda=Pin(sda))
                print(sda, scl, self.oled_width, self.oled_height, disp)

                if disp == 0:
                    from sh1106 import SH1106_I2C
                    self.oled = SH1106_I2C(self.oled_width, self.oled_height, i2c)
                #elif disp == 1:
                    #from ssd1306 import SSD1306_I2C
                    #self.oled = SSD1306_I2C(self.oled_width, self.oled_height, i2c)
            
            elif(msg_type == ONE_BIT_IMAGE):
                p = bytearray(msg)
                if self.oled:
                    if self.oled_width and self.oled_height:
                        fbuf = framebuf.FrameBuffer(p, self.oled_width, self.oled_height,framebuf.MONO_HLSB)
                        
                        self.oled.blit(fbuf,0,0)
                        self.oled.show()
            
            yield
        print("end recv")
    
    async def __send(self):
        old_msg = 0
        old_isqc = 0

        while True:
            #print(self.message_types)
            msg = 0
            if(INPUT_PIN in self.message_types and len(self.pin_in)>0):
                for p in self.pin_in:
                    msg += ((not Pin(p, Pin.IN, Pin.PULL_UP).value())<<p)

                if(msg != old_msg):
                    old_msg = msg
                    if msg != 0:
                        print("sending", msg)
                        msg = INPUT_PIN + str(msg) + "\n"
                        await self.writer.awrite(msg.encode())
                    
            if(READ_NFC in self.message_types):
                nfc = '0'
                if self.nfc_reader:
                    (stat, _ ) = self.nfc_reader.request(self.nfc_reader.REQIDL)
                    if stat == self.nfc_reader.OK:
                        (stat, raw_uid) = self.nfc_reader.anticoll()
                        if stat == self.nfc_reader.OK:
                            nfc=":%02x%02x%02x%02x:" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
                if nfc !='0':
                    to_send = READ_NFC + str(nfc) + "\n"
                    await self.writer.awrite(to_send.encode())
                
            if(READ_ADC in self.message_types and self.adc_pin):
                adc_read = ADC(self.adc_pin)
                to_send = READ_ADC + str(adc_read) + '\n'
                await self.writer.awrite(to_send.encode())
                
            if(READ_I2C in self.message_types):
                #print("reading i2c")
                i2c_msg = 0
                if self.i2c and self.i2c_address and self.i2c_nbytes:
                    i2c_msg = self.i2c.readfrom(self.i2c_address, self.i2c_nbytes)
                    #print(i2c_msg)
                
                if i2c_msg and i2c_msg != old_isqc:
                    old_isqc = i2c_msg
                    to_send = READ_I2C.encode() + i2c_msg + b'\n'
                    await self.writer.awrite(to_send)
            
            if(LATENCY in self.message_types and self.latency):
                to_send = LATENCY.encode() + self.latency + b'\n'
                await self.writer.awrite(to_send)
                self.latency = None
                self.removeMsgType(LATENCY)
            
            yield
        print("end send")

