import wave
import yaml
import numpy as np

from pathlib import Path
from typing import Tuple


def wave_read(filename: Path) -> Tuple[np.ndarray, int]:
    # Utility function that reads the whole `wav` file content into a numpy
    with wave.open(str(filename), 'rb') as f:
        return (
            np.reshape(
                np.frombuffer(
                    f.readframes(f.getnframes()),
                    dtype=f'int{f.getsampwidth()*8}'
                    ), (-1, f.getnchannels())
                ),
            f.getframerate(),
            )


def yaml_dump(data, to_file: Path = None) -> str:
    if to_file:
        with open(to_file, 'w', encoding="utf-8") as f:
            return yaml.dump(data, stream=f, allow_unicode=True)
    return yaml.dump(data, allow_unicode=True)


def yaml_load(from_file: Path) -> dict:
    with open(from_file, 'r', encoding="utf-8") as f:
        return yaml.safe_load(f)
