from recorder import Recorder, Config
from recorder.io import yaml_dump

import socket

from flask import Flask

app = Flask(__name__)

app.secret_key = __name__

# ! Workaround: Global variable because it is not JSON serializable and can't
# ! be stored in Flask.session.
recorder = Recorder(Config.from_yaml(), setup_name=False)
print(yaml_dump(recorder.config))


@app.route('/setup', methods=['GET'])
def setup():
    # TODO get recording name from request
    recorder.setup()
    return str(recorder.next_output.name)


@app.route('/start', methods=['GET'])
def start():
    recorder.start()
    return 'Recording started'


@app.route('/stop', methods=['GET'])
def stop():
    return str(recorder.stop().name)


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    host = s.getsockname()[0]
    app.run(debug=True, host=host)