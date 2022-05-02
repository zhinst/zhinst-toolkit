from urllib.request import urlopen
import os
from pathlib import Path
import fnmatch
import subprocess
import argparse
import typing as t


BASE_EXAMPLE_URL = "https://docs.zhinst.com/zhinst-toolkit/en/latest/examples"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
EXAMPLES_ONLY_SYNC = ["nodetree.md"]
EXCLUDED_FILES = ["README.md"]


def download_example_file(filename: str) -> bytes:
    url = f"{BASE_EXAMPLE_URL}/{filename}"
    try:
        with urlopen(url) as response:
            return response.read()
    except Exception:
        print(url)
        raise


def get_notebook_examples() -> None:
    for example_file in fnmatch.filter(os.listdir(EXAMPLES_DIR), "*.md"):
        if example_file in EXAMPLES_ONLY_SYNC or example_file in EXCLUDED_FILES:
            continue
        example_file = example_file.replace(".md", ".ipynb")
        contents = download_example_file(example_file)
        if contents:
            with open(f"{EXAMPLES_DIR / example_file}", "wb") as f:
                f.write(contents)


def generate_and_sync_example_notebooks(src: t.List[Path]) -> None:
    subprocess.run(["jupytext", "--sync", *src], check=True)


def generate_notebooks(args: argparse.Namespace) -> None:
    if args.src == "local":
        generate_and_sync_example_notebooks([EXAMPLES_DIR / "*.md"])
    else:
        get_notebook_examples()
        generate_and_sync_example_notebooks(
            [EXAMPLES_DIR / file for file in EXAMPLES_ONLY_SYNC]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Notebooks.")
    parser.add_argument("src", help="Source of Notebooks", choices=["local", "remote"])
    generate_notebooks(parser.parse_args())
