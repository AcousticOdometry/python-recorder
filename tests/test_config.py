from recorder.config import Config

def test_init(example_config_path):
    config = Config.from_yaml(example_config_path)
    if not config:
        raise AssertionError