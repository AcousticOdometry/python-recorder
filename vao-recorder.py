import sounddevice as sd
import soundfile as sf
import typer
import yaml

from typing import Optional, List
from PyInquirer import prompt
from datetime import datetime
from pathlib import Path

app = typer.Typer()

DEFAULT_CONFIG_PATH = Path(__file__).parent / 'vao-recorder.yaml'
DEFAULT_OUTPUT_FOLDER = Path(__file__).parent / 'output' / \
    datetime.now().strftime('VAO_%Y-%m-%d_%H-%M-%S')
MICROPHONES = {
    i: d
    for i, d in enumerate(sd.query_devices()) if d['max_input_channels'] > 0
    }


@app.command()
def microphones():
    for id, d in MICROPHONES.items():
        typer.echo(f"{id}:\n\tname: {d['name']}")


@app.command(help='Create a configuration `yaml` file.')
def config(
        output: Optional[Path] = typer.Option(
            DEFAULT_CONFIG_PATH,
            help="Path to where the configuration yaml file should be written."
            )
    ) -> dict:
    config = {'microphones': {}, 'cameras': {}}
    while typer.confirm(
        f"Do you want to add {'another' if config['microphones'] else 'a'} "
        "microphone?"
        ):
        device_id = prompt({
            'type':
                'list',
            'name':
                'device_id',
            'message':
                f"Select the microphone to add to the configuration:",
            'choices': [{
                'name': f"{i} {d['name']}",
                'value': i
                } for i, d in MICROPHONES.items()],
            })['device_id']
        config['microphones'][device_id] = {
            'name': MICROPHONES[device_id]['name'],
            'samplerate': MICROPHONES[device_id]['default_samplerate'],
            'channels': MICROPHONES[device_id]['max_input_channels'],
            }
    with open(output, 'w') as f:
        f.write(yaml.dump(config))
    return config


def get_config(path=DEFAULT_CONFIG_PATH) -> dict:
    if path.exists():
        with open(path, 'r') as f:
            _config = yaml.safe_load(f)
    if not _config:
        typer.secho(
            f'No configuration found in {path}. Generate one.',
            fg='black',
            bg='yellow'
            )
        _config = config(path)
    return _config


def get_audio_stream(
    device_id: int,  # Device identifier
    output_path: Path,  # Path to where the audio file should be written
    samplerate: int = None,  # Sample rate
    channels: int = None,  # Number of channels
    **
    stream_kwargs,  # Additional keyword arguments for sounddevice.InputStream
    # https://python-sounddevice.readthedocs.io/en/0.4.4/api/streams.html#sounddevice.InputStream
    ) -> sd.InputStream:
    f = sf.SoundFile(
        output_path, 'x', samplerate=int(samplerate), channels=int(channels)
        )
    return sd.InputStream(
        device=device_id,
        samplerate=samplerate,
        channels=channels,
        callback=lambda data, frames, time, status: f.write(data),
        finished_callback=f.close,
        **stream_kwargs
        )


def get_audio_streams(
        config: dict,  # Configuration dictionary
        output_folder: Path,  # Folder where the audio files should be written
    ) -> List[sd.InputStream]:
    streams = []
    for i, (_id, mic) in enumerate(config.get('microphones', {}).items()):
        name = f"{_id} {mic.pop('name', '')}"
        try:
            streams.append(
                get_audio_stream(
                    device_id=_id,
                    output_path=output_folder / f'audio{i}.wav',
                    **mic
                    )
                )
        except TypeError as e:
            typer.secho(
                f'Failed to open microphone `{name}`, review its '
                f'configuration {mic}\nError: {e}',
                fg='red'
                )
            raise e
        # Write configuration in a yaml file
        with open(output_folder / f'audio{i}.yaml', 'w') as f:
            f.write(yaml.dump(mic))
    return streams


def record_video(device_id, output_folder):
    pass


@app.command(help='Record visual and acoustic data.')
def record(
    config_path: Optional[Path] = typer.Option(
        DEFAULT_CONFIG_PATH,
        help="""
        Path to a `yaml` config file. Run `config` command to generate one."""
        ),
    output_folder: Optional[Path] = typer.Option(
        DEFAULT_OUTPUT_FOLDER,
        help="""
        Path to a folder where the recorded data and the recording
        configuration will be stored."""
        ),
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)

    # Setup audio recording
    audio_streams = get_audio_streams(config, output_folder)

    # Setup video recording
    for camera in config.get('cameras', []):
        # TODO read video cameras
        typer.echo(camera)

    # Start the recording
    for stream in audio_streams:
        stream.start()
    # Wait for user input
    input('Press `Enter` to stop recording.')
    # Cleanup the recording
    for stream in audio_streams:
        stream.stop()
        stream.close()
    return output_folder


@app.command(
    help="""
    Record 5 seconds from the configured microphones and play back the audio of
    each recording."""
    )
def test_audio(
    config_path: Optional[Path] = typer.Option(
        DEFAULT_CONFIG_PATH,
        help="""
        Path to a `yaml` config file. Run `config` command to generate one."""
        ),
    output_folder: Optional[Path] = typer.Option(
        DEFAULT_OUTPUT_FOLDER,
        help="""
        Path to a folder where the recorded data and the recording
        configuration will be stored."""
        ),
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    print(sf._libname)
    print(sf.available_formats())
    # Record 5 seconds of audio
    audio_streams = get_audio_streams(config, output_folder)
    for stream in audio_streams:
        stream.start()
    with typer.progressbar(range(50), label='Recording...') as progress:
        for _ in progress:
            sd.sleep(100)  # milliseconds
    for stream in audio_streams:
        stream.stop()
        stream.close()
    sd.sleep(1000)
    # Play audio
    for _file in output_folder.glob('audio*.wav'):
        typer.echo(f'Playing {_file}')
        with open(_file, 'r') as f:
            data, fs = sf.read(f, always_2d=True)
            sd.play(data, samplerate=fs)


if __name__ == '__main__':
    app()