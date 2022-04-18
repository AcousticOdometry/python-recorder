from recorder.device import Device
from recorder.io import wave_read

import wave
import sounddevice as sd

from pathlib import Path
from inspect import signature


class Microphone(Device):
    stream_keyword_arguments = [
        str(s) for s in signature(sd.RawInputStream).parameters
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert 'index' in self.config
        assert 'samplerate' in self.config
        assert 'channels' in self.config
        # Signature from sounddevice.RawInputStream
        stream_kwargs = {
            k: self.config[k]
            for k in self.config.keys() if k in self.stream_keyword_arguments
            }
        self.stream = self._get_stream(
            device=self.config['index'],
            output_path=self.output_file.with_suffix('.wav'),
            **stream_kwargs
            )

    @staticmethod
    def _get_stream(
        device: int,  # Device identifier
        output_path: Path,  # Path to where the audio file should be written
        samplewidth: int = 2,  # Sample width in bytes
        samplerate: int = None,  # Sample rate
        channels: int = None,  # Number of channels
        **stream_kwargs,  # Additional keyword arguments for sd.RawInputStream
        # https://python-sounddevice.readthedocs.io/en/0.4.4/api/streams.html#sounddevice.InputStream
        ) -> sd.InputStream:
        f = wave.open(str(output_path), 'wb')
        f.setnchannels(int(channels))
        f.setframerate(int(samplerate))
        f.setsampwidth(samplewidth)
        return sd.RawInputStream(
            device=device,
            dtype=f'int{samplewidth*8}',
            samplerate=samplerate,
            channels=channels,
            callback=lambda data, N, t, status: f.writeframesraw(data),
            finished_callback=f.close,
            **stream_kwargs
            )

    @classmethod
    def find(cls) -> dict:
        devices = {}
        for idx, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                devices[idx] = {
                    'name': d['name'],
                    'index': idx,
                    'samplerate': int(d['default_samplerate']),
                    'channels': int(d['max_input_channels']),
                    }
        return devices

    def _start(self):
        self.stream.start()

    def _stop(self):
        self.stream.stop()
        self.stream.close()

    @classmethod
    def show_results(cls, from_folder):
        for _file in from_folder.glob(f'{repr(cls)}*.wav'):
            print(f'Playing {_file}')
            with open(_file.with_suffix('.yaml'), encoding='utf-8') as f:
                print(f.read())
            data, fs = wave_read(_file)
            sd.play(data, samplerate=fs, blocking=True)