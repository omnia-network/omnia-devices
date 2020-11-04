# firmware v 0.6.1
import struct
import asyncio
from bleak import BleakScanner

### Omnia libraries ###
from omniaMessageTypes      import OmniaMessageTypes as OMT
### --- ###

class OmniaRPi:
    def __init__(self, device_type, touch=None):
        
        self.send_type = None  # 0: touch, 1: nfc, 2: adc, 3: i2c, 4: ble, 5: latency
        self.old_send_type = None

        ## Asyncio ##
        self.loop = asyncio.new_event_loop()

        ## Socket ##
        self.reader = None
        self.writer = None

        ## BLE ##
        self.stopScan = False
        self.ble = None
        self.bleDevices = []
        self.ble_task = None

        ## Received Data ##
        self.message_types = [OMT.LATENCY]

        self.stream_types = ['S', 'j', 'v', 'a', 'd', 'l']

        self.old_msg = ''

        ## Display ##
        self.display = None
        self.display_task = None

        ## Audio ##
        self.audio = None

        ## Touch ##
        self.touch = None

        ## Latency ##
        self.latency_msg = None

        self.init_type(device_type, touch)
    
    def init_type(self, device_type, touch):
        ## Device Type ##
        if device_type == "ili9341":
            from screen import Screen

            self.display = Screen(320, 240)
        elif device_type == "audio":
            from audio import Audio

            self.audio = Audio()
        
        ## Touch ##
        if touch == 'xpt2046':
            from touch import TouchScreen

            self.touch = TouchScreen()
            self.send_type = 0

    async def recv_msg(self):
        # Read message length and unpack it into an integer
        raw_msglen = await self.recvall(4)
        if not raw_msglen:
            return b'00'
        msglen = struct.unpack('>I', raw_msglen)[0]
        # Read the message data
        return await self.recvall(msglen)

    async def recvall(self, n):
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

    async def scan_ble(self):
        while not self.stopScan:
            async with BleakScanner() as scanner:
                await asyncio.sleep(2.0)
                self.bleDevices = await scanner.get_discovered_devices()
            '''for d in devices:
                print(d)'''
    
    def setSocket(self, socket):
        self.reader, self.writer = self.loop.run_until_complete(asyncio.open_connection(sock=socket))

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
        print("begin recv cycle")
        while True:
            s = bytes(await self.recv_msg())
            
            msg_type = chr(s[0])
            print(msg_type)
            
            msg = None
            args = []

            if not msg_type in self.stream_types:
                msg = s.decode()[1:]
                args = list(map(int, msg.split("-")))
                print(args)
            else:
                msg = s[1:]

            ### message cases ###

            if(msg_type == LATENCY):
                self.latency_msg = msg
                self.addMsgType(msg_type)
            
            if(msg_type == OMT.READ_BLE):    # scan BLE
                flag = args[0]

                self.stopScan = not flag
                
                if flag:
                    self.addMsgType(OMT.BLE)
                    self.ble_task = self.loop.create_task(self.scan_ble())
                else:
                    self.removeMsgType(OMT.BLE)
                    self.ble_task.cancel()
                    self.bleDevices = []
            
            elif(msg_type == OMT.START_STOP_VIDEO_STREAM):  # stream video
                flag = args[0]
                
                self.display.stopStream = not flag

                if flag:
                    self.display_task = self.loop.create_task(self.display.draw_stream())
                else:
                    self.display_task.cancel()
            
            elif(msg_type == OMT.VIDEO_FRAME):  # recv video frame

                if self.display:
                    self.loop.create_task(self.display.recv_frame(msg))

            elif(msg_type == OMT.SET_AUDIO):  # start audio
                flag = args[0]

                if flag:
                    framerate = args[1]
                    channels = args[2]
                    sampwidth = args[3]
                    chunk_size = args[4]

                    if self.audio:
                        self.audio.start_stream(framerate, channels, sampwidth, chunk_size)
                else:
                    if self.audio:
                        self.audio.stop_stream()
            
            elif(msg_type == OMT.AUDIO_CHUNK):  # recv audio frame
                if self.audio:
                    self.audio.stream_audio(msg)
            
            elif(msg_type == OMT.RGBA_IMAGE):  # recv display

                if self.display:
                    self.display.setDisplay(msg)
            
            elif(msg_type == OMT.LATENCY):  # respond to latency calculator
                self.latency_msg = msg
                self.addMsgType(OMT.LATENCY)
            
            await asyncio.sleep(0.01)
        print("end recv")
    
    def sendMsg(self, msg, msg_type):
        if msg != '' and msg != self.old_msg:
            self.old_msg = msg
            to_send = msg_type + msg + '\n'
            self.writer.write(to_send.encode())

    async def __send(self):
        print("begin send cycle")
        
        while True:

            if self.touch:  # stream touch coordinates
                x, y = self.touch.get_touch_coords()
                #print(x,y)

                if x > 0 and y > 0:
                    msg = str(x) + "," + str(y)
                    self.sendMsg(msg, OMT.TOUCHSCREEN)
                    
            if(OMT.READ_BLE in self.message_types and len(self.bleDevices)>0):
                ble_result = ''
                for d in self.bleDevices:
                    ble_result += str(d.rssi)+'+'+str(d.name)+","

                self.sendMsg(ble_result, OMT.READ_BLE)
            
            if(OMT.LATENCY in self.message_types and self.latency_msg):

                #print("responding to latency")
                msg = self.latency_msg.decode()
                
                self.sendMsg(msg, OMT.LATENCY)

                self.latency_msg = None
                self.removeMsgType(OMT.LATENCY)

            await self.writer.drain()
            
            await asyncio.sleep(0.1)
        print("end send")
