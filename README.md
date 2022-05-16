# python-recorder

Device independent framework for synchronized recording. Originally designed to
record audio and video from a Realsense camera and several microphones. This
framework is designed for researchers collecting multimodal datasets. It
provides an easy to use command line application that allows to configure, test and
use the available sensors in the host machine while providing intuitive mechanisms 
to synchronize the recording devices with the specific event that one wants to record. 
The framework can be divided in two main features:

## Devices
They provide a common interface to initialize, `start` and `stop` a recording,
whether is a camera, a microphone or any other sensor. When the recording is
stopped, device parameters (e.g., `samplerate` in microphones, `framerate` in
cameras) as well as a `start_timestamp` and an `end_timestamp` are saved
together with the recorded data which allows fine synchronization of data from
multiple devices in post-processing.

Devices are configurable through a command line application, which searches for
available options in the host machine. At the same time, they are saved in a
[`yaml` formatted text file](./example-config.yaml). Which allows easy access
to device exclusive configuration parameters.

Multiple devices compose a [`Recorder` object](./recorder/recorder.py), which
is responsible for initializing all its devices, setup an output folder for the
recordings, and start and stop the recording.

Adding new devices classes is simple, one just needs to extend the [`Device`
class](./recorder/device/device.py) and override its abstract methods (`find`,
`_start`, `_stop` and `show_results`).

## Listeners
Researchers usually want to synchronize the recording with a specific event, a
test or experiment, which can be triggered by a different machine. A `Listener`
is an interface between a `Recorder` and an external event. At the moment, the
only one available is a [`Localhost`
listener](./recorder/listener/localhost.py). Which triggers the recording
according to `GET` requests through the local network. But additional listeners
can be added by extending the [`Listener`
class](./recorder/listener/listener.py) and overriding its abstract methods. An
example of another listener would be a `ROS` node that subscribes to a specific
topic and triggers the recording according to a specific set of messages.

Listeners can be setup through the `listen`. This command does not initialize
the devices. The listener is responsible of executing `recorder.setup()` as it
sees fit. In the case of the `localhost` listener, a `GET` request to the
`/setup` endpoint is necessary before trying to start the recording via the
`/start` endpoint.

# Setup
It is recommended to use a virtual environment in order to isolate the
installation, as it provides a command line interface named `recorder` that can
conflict with other system packages.

```
python -m venv venv
````

Activate the environment on Windows:

```
venv\Scripts\activate
```

or on MacOS and Linux:

```
source venv/bin/activate
```

Install from [pypi](https://pypi.org/project/python-recorder/). There are
optional dependencies that define which devices and listeners are available,
due to the fact some of these dependencies are not available for all operative
systems. Check [extras](#extras) for more information about it.
```
pip install python-recorder[all]
```

or install this repository to use the latest development versions.
```
pip install git+https://github.com/AcousticOdometry/python-recorder.git[all]
```

## Extras
Extras can be installed through [the `pip install`
command](https://pip.pypa.io/en/stable/cli/pip_install/#requirement-specifiers)
by specifying them at the end of the package name:

```
pip install python-recorder[extra_one,extra_two]
```

The available extras are defined in [`pyproject.toml`](./pyproject.toml) and
are described here:

- `realsense`: [Intel
    Realsense](https://www.intel.com/content/www/us/en/architecture-and-technology/realsense-overview.html)
    devices depend on [pyrealsense2](https://pypi.org/project/pyrealsense2/).
- `all`: All the extras defined above.

# Usage
Check the usage with the `--help` option:
```
recorder --help
```

# Workflow

Configure the devices to be used. One can always modify the configuration
manually in the generated `yaml` file.
```
recoder config
```

Test that the chosen audio devices are working
```
recorder test microphone
```

Record an experiment with the configured devices
```
recorder record
```

Listen to `GET` requests through the local network
```
recorder listen localhost
```

# Contributing
We are open to contributions. Please, feel free to open an issue or pull
request with any improvement or bug report. The framework is simple and easily
extensible, it should fit easily in many projects.

## TODO

- [ ] ROS listener
- [ ] Complete test suite
- [ ] Camera device with `OpenCV`
- [ ] Speedup the configuration file creation with compiled code?
