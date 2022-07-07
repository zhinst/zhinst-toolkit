"""Helper script for developers.

The script creates a symbolic link between existing toolkit and
Python environment directories.

By running the script, zhinst-toolkit is added to the ``zhinst`` package namespace
for the given Python environment.

Windows: Requires administration privileges.

zhinst-toolkit must be installed before running the script.

Running the script:

    >>> python scripts/zhinst_toolkit_symlink.py
"""
import os
import sysconfig
from pathlib import Path


SRC_DIR = Path(Path(__file__).parent.parent / Path("src/zhinst/toolkit")).resolve()
DEST_DIR = Path(sysconfig.get_path("purelib")) / "zhinst/toolkit"


def create_symlink(src: Path, dest: Path) -> None:
    """Create symbolic link between working dir and python environment.

    Create symbolic link between existing toolkit and
    Python environment directories.

    Args:
        src: Toolkit directory (e.g. a/b/src/zhinst/toolkit).
        dest: Python environment directory
    """
    try:
        # Windows: Requires administrator when running tests without symlink
        # Otherwise Symlink must be made manually to add toolkit to Python site-packages
        os.symlink(src, dest)
        print(f"Symlink created. Source: {src}, Destination: {dest}")
    except FileExistsError:
        print(f"Destination: {dest} already exists.")


if __name__ == "__main__":
    create_symlink(SRC_DIR, DEST_DIR)
