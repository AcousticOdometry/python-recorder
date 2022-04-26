from recorder.listener import Listener

import socket

from flask import Flask, request, Response

# Troubleshooting:
# https://stackoverflow.com/questions/62705271/connect-to-flask-server-from-other-devices-on-same-network


class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    def __call__(self, *args):
        # Perform the action
        answer = self.action()
        # Create the answer (bundle it in a correctly formatted HTTP answer)
        self.response = Response(answer, status=200, headers={})
        # Send it
        return self.response


class Localhost(Listener):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.app = Flask('python-recorder')
        self.app.add_url_rule(
            '/setup', '/setup', EndpointAction(self.setup), methods=['GET']
            )
        self.app.add_url_rule(
            '/start', '/start', EndpointAction(self.start), methods=['GET']
            )
        self.app.add_url_rule(
            '/stop', '/stop', EndpointAction(self.stop), methods=['GET']
            )

    def setup(self):
        name = request.args.get('name', None)
        self.recorder.setup(name=name)
        return str(self.recorder.next_output.name)

    def start(self):
        self.recorder.start()
        return 'Recording started'

    def stop(self):
        return str(self.recorder.stop().name)

    def listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host = s.getsockname()[0]
        self.app.run(debug=True, host=host)
