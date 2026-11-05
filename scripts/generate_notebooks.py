"""A script to sync the example Notebooks with their Markdown sources."""

import typing as t
from pathlib import Path

from jupytext import cli as jupytext_cli

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def generate_and_sync_example_notebooks(src: t.List[Path]) -> None:
    """Generate and sync given source files to notebooks.

    Args:
        src: Source files
    """
    str_path = [str(path) for path in src]
    jupytext_cli.jupytext(["--sync", *str_path])


if __name__ == "__main__":
    generate_and_sync_example_notebooks([EXAMPLES_DIR / "*.md"])
