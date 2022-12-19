import pathlib
import re
import pytest
import yaml


EXAMPLES_PATH = pathlib.Path("examples")


def match_regex_in_markdown(markdown_file: pathlib.Path, exp_to_match: str) -> bool:
    """Check if a regex is matched inside a markdown file.

    Args:
        markdown_file: Path to the markdown file where the regex is to be searched.
        exp_to_match: Regular expression to be matched.

    Returns:
        Flag if the regex has been matched.
    """
    with open(markdown_file, "r") as f:
        for line in f:
            match = re.search(exp_to_match, line)
            if match is not None:
                return True
    return False


def get_markdown_files() -> pathlib.Path:
    """Collect all the markdown files contained in the examples path.

    Yields:
        The path to a markdown file.

    """
    with open(EXAMPLES_PATH / "test.spec.yml", "rb") as f:
        test_spec = yaml.load(f, Loader=yaml.Loader)

    md_list = EXAMPLES_PATH.glob("*.md")
    for md_file in md_list:
        # README.md should not be checked
        if md_file.stem == "README":
            continue
        elif "skip" in test_spec[md_file.stem] and test_spec[md_file.stem]["skip"]:
            continue
        else:
            yield md_file


@pytest.mark.parametrize(
    "input_file", get_markdown_files(), ids=lambda input_file: input_file.stem
)
def test_examples_regex_match(input_file: pathlib.Path):
    assert match_regex_in_markdown(
        input_file, '"DEVXXXX"'
    ), f'Expression "DEVXXXX" not found in {input_file.name}'

    assert match_regex_in_markdown(
        input_file, '"localhost"'
    ), f'Expression "localhost" not found in {input_file.name}'
