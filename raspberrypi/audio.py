from pyaudio import PyAudio

class Audio:
    def __init__(self):
        self.p = PyAudio()
        self.stream = None
        self.chunk_size = None
        #self.samples = bytes(chunk_size)
    
    def start_stream(self, framerate, channels, sampwidth, chunk_size):
        self.stream = self.p.open(format=self.p.get_format_from_width(sampwidth),
                    channels=channels,
                    rate=framerate,
                    output=True)
        self.chunk_size = chunk_size

    def stream_audio(self, chunk):
        samples = bytes(chunk)
        if len(samples)>0 and self.stream:
            self.stream.write(samples)

    def close_stream(self):
        self.stream.stop_stream()
        self.stream.close()

        self.p.terminate()