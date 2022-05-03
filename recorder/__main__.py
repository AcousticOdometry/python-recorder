from recorder.config import DEFAULT_CONFIG_PATH, DEFAULT_OUTPUT_FOLDER
from recorder.device import Device, DEVICE_CLASSES
from recorder.listener import Listener, LISTENER_CLASSES
from recorder.io import yaml_dump
from recorder import Recorder, Config

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
LISTENER_CLASS_ARGUMENT = typer.Argument(
    'localhost',
    metavar='LISTENER_CLASS',
    help=(
        "Case independent name of the listener class to use. Available "
        f"options: {[d for d in DEVICE_CLASSES.keys()]}."
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


def get_device_class(name: str) -> Device:
    try:
        return DEVICE_CLASSES[name.lower()]
    except KeyError:
        raise RuntimeError(
            f"Invalid device class `{name}`. Available options: "
            f"{list(DEVICE_CLASSES.keys())}"
            )


def get_listener_class(name: str) -> Listener:
    try:
        return LISTENER_CLASSES[name.lower()]
    except KeyError:
        raise RuntimeError(
            f"Invalid listener class `{name}`. Available options: "
            f"{list(LISTENER_CLASSES.keys())}"
            )


@app.command(help="Display the available devices")
def show(
        device_class: Optional[str] = DEVICE_CLASS_ARGUMENT,
        verbose: bool = VERBOSE_OPTION
    ):
    if device_class:
        device_classes = [get_device_class(device_class)]
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
    choices = {}
    index = 0
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
        choices[index] = devices[_id]
        index += 1
    return choices


@app.command(help="Create a configuration `yaml` file.")
def config(output: Path = DEFAULT_CONFIG_PATH_OPTION) -> dict:
    config = {}
    for name, device_class in DEVICE_CLASSES.items():
        device_config = config_device_class(device_class)
        if device_config:
            config[name] = device_config
    yaml_dump(config, to_file=output)
    typer.echo(
        f"Configuration file written to {output}, it can be edited manually. "
        "Check the repository for an explained example file "
        "https://github.com/AcousticOdometry/VAO-recorder/blob/main/example-config.yaml"
        )
    return config


def get_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    try:
        return Config.from_yaml(path)
    except AttributeError:
        raise RuntimeError(
            f"No configuration found in {path}. Generate one with the "
            "`config` command."
            )


@app.command(help="Record data from the configured devices")
def record(
    seconds: int = typer.Argument(None, help="Number of seconds to record"),
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ):
    config = get_config(config_path)
    recorder = Recorder(config, output_folder)
    if typer.confirm("Recording ready, start?", default=True):
        output_folder = recorder(seconds=seconds)
        typer.echo(f"Recording finished, data saved to {output_folder}")


@app.command(help='Listen to an external command to start recording')
def listen(
    listener_class: str = LISTENER_CLASS_ARGUMENT,
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    # TODO pass kwargs to listener. Or make subcommands for each listener
    ):
    config = get_config(config_path)
    recorder = Recorder(config, output_folder, setup_name=False)
    listener = get_listener_class(listener_class)(recorder)
    listener.listen()


@app.command(help="Test device recording")
def test(
    device_class: Optional[str] = DEVICE_CLASS_ARGUMENT,
    device_id: Optional[int] = DEVICE_ID_ARGUMENT,
    config_path: Optional[Path] = DEFAULT_CONFIG_PATH_OPTION,
    output_folder: Optional[Path] = DEFAULT_OUTPUT_FOLDER_OPTION,
    ):
    if not device_id:
        config = get_config(config_path)
        if device_class:
            # Filter to only the devices of the given class
            config = Config({
                d_class: ds
                for d_class, ds in config.items() if d_class == device_class
                })
            if not config:
                typer_warn(
                    f"No device of class `{device_class}` found in "
                    f"{config_path}"
                    )
                return
        recorder = Recorder(config, output_folder)
        output_folder = recorder(seconds=5)
        for _device_class in config.keys():
            DEVICE_CLASSES[_device_class].show_results(output_folder)
    else:
        # Both device_class and device_id are given
        devices = get_device_class(device_class).find()
        try:
            device = devices[device_id]
        except KeyError:
            raise AttributeError(
                f'Invalid device id `{device_id}` for class `{device_class}`'
                )
        config = Config({device_class: {device_id: device}})
        recorder = Recorder(config, output_folder)
        output_folder = recorder(seconds=5)
        DEVICE_CLASSES[device_class].show_results(output_folder)


def main():
    # Launch the command line application
    try:
        app(prog_name='recorder')
    except RuntimeError as e:
        typer.secho(str(e), fg='red')


if __name__ == '__main__':
    main()