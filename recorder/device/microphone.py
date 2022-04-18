from recorder.device import Device

import sounddevice as sd

from pathlib import Path


class Microphone(Device):

    def __init__(
            self, *args, index: int, samplerate: int, channels: int, **kwargs
        ):
        super().__init__(*args, **kwargs)
        self.index = index
        self.samplerate = samplerate
        self.channels = channels
        self.stream = self._get_stream(
            device=index,
            output_path=self.output_file.with_suffix('.wav'),
            )

    @classmethod
    def find(cls) -> dict:
        devices = {}
        for idx, d in enumerate(sd.query_devices()):
            if d['max_input_channels'] > 0:
                devices[idx] = {
                    'samplerate': int(d['default_samplerate']),
                    'channels': int(d['max_input_channels']),
                    'name': d['name'],
                    'index': idx,
                    }
        return devices

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

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop()
        self.stream.close()
        # Write start timestamp
        # with open(self.output_folder / 'audio_start.txt', 'w') as f:
        #     f.write(str(datetime.now().timestamp()))