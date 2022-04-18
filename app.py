from recorder.settings import DEFAULT_CONFIG_PATH, DEFAULT_OUTPUT_FOLDER
from recorder.device import Device
from recorder.io import yaml_dump, yaml_load

import typer

from pathlib import Path
from typing import Optional
from PyInquirer import prompt

# Command line application
app = typer.Typer(
    add_completion=False,
    help=__doc__,
    )

DEFAULT_OUTPUT_FOLDER_OPTION = typer.Option(
    DEFAULT_OUTPUT_FOLDER,
    help="""
    Path to a folder where the recorded data and the recording configuration
    will be stored."""
    )
DEFAULT_CONFIG_PATH_OPTION = typer.Option(
    DEFAULT_CONFIG_PATH,
    help="Path to a `yaml` config file. Run `config` command to generate one."
    )

DEVICE_CLASSES = {cls.__name__.lower(): cls for cls in Device.__subclasses__()}
DEVICE_CLASS_ARGUMENT = typer.Argument(
    None,
    metavar='DEVICE_CLASS',
    help=(
        "Case independent name of the device class to use. Available options: "
        f"{[d for d in DEVICE_CLASSES.keys()]}."
        )
    )
DEVICE_ID_ARGUMENT = typer.Argument(
    None,
    metavar='DEVICE_ID',
    help=(
        "Numerical id of the device to use. Use the show command to see the available devices for each device class."
        )
    )
VERBOSE_OPTION = typer.Option(False, "--verbose", "-v", help="Verbose output.")


def typer_warn(message: str):
    return typer.secho(message, bg='black', fg='yellow')


def choose(message: str, choices: list):
    # Utility function that asks the user to configure the devices
    return prompt({
        'type': 'list',
        'name': 'choice',
        'message': message,
        'choices': choices,
        })['choice']


def wait(seconds: int = 4, label: str = 'Recording...', **kwargs):
    with typer.progressbar(range(seconds * 10), label=label, **kwargs) as p:
        for _ in p:
            sd.sleep(100)


@app.command(help='Display the available devices')
def show(
        device_class: Optional[str] = DEVICE_CLASS_ARGUMENT,
        verbose: bool = VERBOSE_OPTION
    ):
    if device_class:
        try:
            device_classes = [DEVICE_CLASSES[device_class.lower()]]
        except KeyError:
            raise RuntimeError(
                f'Invalid device class `{device_class}`. Available options: '
                f'{list(DEVICE_CLASSES.keys())}'
                )
    else:
        device_classes = DEVICE_CLASSES.values()
    for cls in device_classes:
        devices = cls.find()
        if devices:
            if not verbose:
                devices = {i: d['name'] for i, d in devices.items()}
            typer.echo(f'{cls}:\n' + yaml_dump(devices))
        else:
            typer_warn(f"Could not find {cls} devices")


def config_device_class(device: Device) -> dict:
    choices = []
    devices = device.find()
    if not devices:
        typer_warn(f"Could not find {device} devices")
        return choices
    while typer.confirm(
        f"Add {'another' if choices else 'a'} {device} device?"
        ):
        _id = choose(
            message=f"Select the {device} to add to the configuration:",
            choices=[{
                'name': f"{_id} {d['name']}",
                'value': _id
                } for _id, d in devices.items()]
            )
        choices.append(devices[_id])
    return {i: c for i, c in enumerate(choices)}


@app.command(help='Create a configuration `yaml` file.')
def config(output: Path = DEFAULT_CONFIG_PATH_OPTION) -> dict:
    config = {}
    for name, device_class in DEVICE_CLASSES.items():
        config[name] = config_device_class(device_class)
    yaml_dump(config, to_file=output)
    typer.echo(
        f"Configuration file written to {output}. Remember that it can be "
        "edited manually. Check the repository for an explained example file "
        "https://github.com/AcousticOdometry/VAO-recorder/blob/main/example-config.yaml"
        )
    return config


def get_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    _config = None
    if path.exists():
        _config = yaml_load(path)
    if not _config:
        typer_warn(f"No configuration found in {path}. Generate one.")
        _config = config(path)
    return _config


def record():
    pass


@app.command(help='Test the available devices of a certain [device_class]')
def test(
        device_class: Optional[str] = DEVICE_CLASS_ARGUMENT,
        device_id: Optional[int] = DEVICE_ID_ARGUMENT
    ):
    if not device_id:
        config = get_config()
        if not device_class:
            pass
    else:
        # Both device_class and device_id are given
        pass


if __name__ == '__main__':
    # Launch the command line application
    try:
        app()
    except RuntimeError as e:
        typer.secho(str(e), fg='red')