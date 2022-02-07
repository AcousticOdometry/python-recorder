import sounddevice as sd
import soundfile as sf
import numpy as np

from pathlib import Path

def record_audio(device, output_folder):
    pass

def record_video():
    pass

def record():
    pass

def config():
    pass

if __name__ == '__main__':
    print(sd.query_devices())
    fs = 48000 # Sample rate
    duration = 5 # Duration in seconds
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=2, blocking=True)
    sf.write('output/output.wav', myrecording, fs)
    sd.play(myrecording, fs)
    sd.wait()
