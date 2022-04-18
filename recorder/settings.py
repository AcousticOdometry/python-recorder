from pathlib import Path
from datetime import datetime

DEFAULT_CONFIG_PATH = Path.cwd() / 'vao-recorder.yaml'

DEFAULT_OUTPUT_FOLDER = Path.cwd() / 'output' / \
    datetime.now().strftime('VAO_%Y-%m-%d_%H-%M-%S')

# class Config:
