import sounddevice as sd
import soundfile as sf
import typer
import yaml

from PyInquirer import prompt
from functools import partial
from typing import Optional
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


def record_audio(
        device_id: int,
        output_path: Path,
        samplerate: int = None,
        channels: int = None,
        **stream_kwargs
    ) -> sd.InputStream:
    with sf.SoundFile(
        output_path, 'x', samplerate=samplerate, channels=channels
        ) as f:
        return sd.InputStream(
            device=device_id,
            samplerate=samplerate,
            channels=channels,
            callback=lambda data, frames, time, status: f.write(data),
            **stream_kwargs
            )


def record_video(device_id, output_folder):
    pass


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
    # yaml microphones should match the call signature of sounddevice.InputStream
    # https://python-sounddevice.readthedocs.io/en/0.4.4/api/streams.html#sounddevice.InputStream
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


@app.command(help='Record visual and acoustic data.')
def record(
        config_path: Optional[Path] = typer.Option(
            DEFAULT_CONFIG_PATH,
            help="""
            Path to a `yaml` config file. Run `config` command to generate one.
            """
            ),
        output_folder: Optional[Path] = typer.Option(
            DEFAULT_OUTPUT_FOLDER,
            help="""
            Path to a folder where the recorded data and the recording
            configuration will be stored."""
            )
    ) -> Path:
    config = get_config(config_path)
    output_folder.mkdir(exist_ok=True, parents=True)
    streams = []
    for i, (_id, mic) in enumerate(config.get('microphones', {}).items()):
        name = f"{_id} {mic.pop('name', '')}"
        try:
            streams.append(
                record_audio(
                    device_id=_id,
                    output_path=output_folder / f'audio{i}.wav',
                    **mic
                    )
                )
        except TypeError as e:
            typer.secho(
                f'Failed to open microphone `{name}`, review the '
                f'configuration file {config_path}\nError: {e}',
                fg='red'
                )
            raise typer.Exit(code=1)
        # TODO write metadata in audio{i}.txt
    for camera in config.get('cameras', []):
        typer.echo(camera)


if __name__ == '__main__':
    app()

    # fs = 48000  # Sample rate
    # duration = 5  # Duration in seconds
    # myrecording = sd.rec(
    #     int(duration * fs), samplerate=fs, channels=2, blocking=True
    #     )
    # config = get_config()
    # config = {'microphones': {None: {'samplerate'}}}
    # sf.write('output/output.wav', myrecording, fs)
    # sd.play(myrecording, fs)
    # sd.wait()
