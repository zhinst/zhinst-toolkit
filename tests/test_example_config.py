import yaml
import os
from glob import glob
from pathlib import Path

EXAMPLES_DIRECTORY = "examples/"


def test_config_existence():
    assert os.path.exists(EXAMPLES_DIRECTORY + "test.spec.yml")


def test_example_config():
    with open(EXAMPLES_DIRECTORY + "test.spec.yml", "rb") as f:
        test_spec = yaml.load(f, Loader=yaml.Loader)

    examples_list = glob(EXAMPLES_DIRECTORY + "*.md")

    for example in examples_list:
        example_name = Path(example).name.split(".")[0]
        if example_name == "README":
            continue

        # Check that the notebook is in the config file
        assert (
            example_name in test_spec
        ), f'Example "{example_name}" was not included in the configuration file.'

        # If test has to be skipped, return
        if "skip" in test_spec[example_name] and test_spec[example_name]["skip"]:
            return

        # Check that it has the device id specified
        assert (
            "device_type" in test_spec[example_name]
        ), f'No device_type was specified for the example "{example_name}".'

        # Check that the device id was written
        assert (
            test_spec[example_name]["device_type"] != None
        ), f'The field "device_type" is empty for the example "{example_name}".'
