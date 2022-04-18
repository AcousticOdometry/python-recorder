import pytest

from pathlib import Path

@pytest.fixture(scope="session")
def example_config_path():
    return Path(__file__).parent.parent / 'example-config.yaml'