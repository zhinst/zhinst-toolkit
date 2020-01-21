##
# -----------------------------------------------------------------------------
# @copyright Copyright (c) 2019 Zurich Instruments AG - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# @author hossein.ajallooiean@zhinst.com
# @date 21.11.2019
# -----------------------------------------------------------------------------
##


import os
import inspect
import setuptools
import sys


requirements = [
    "numpy>=1.13",
    "setuptools>=40.1.0"
]


if not hasattr(setuptools,
               'find_namespace_packages') or not inspect.ismethod(
                    setuptools.find_namespace_packages):
    print("Your setuptools version:'{}' does not support PEP 420 "
          "(find_namespace_packages). Upgrade it to version >='40.1.0' and "
          "repeat install.".format(setuptools.__version__))
    sys.exit(1)


version_path = os.path.abspath(os.path.join('VERSION.txt'))
with open(version_path, 'r') as fd:
    version = fd.read().rstrip()

setuptools.setup(
    name="interface",
    version=version,
    description="Zurich Instrument tools for quantum information science",
    url="https://gitlab.zhinst.com/labone/qccs/qccs-interface",
    author="Zurich Instruments Development Team",
    author_email="hossein.ajallooiean@zhinst.com",
    license="Apache 2.0",
    classifiers=[
        "Environment :: Console",
        "License :: Other/Proprietary License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering",
    ],
    keywords="zhinst sdk quantum",
    packages=setuptools.find_namespace_packages(exclude=['test*']),
    install_requires=requirements,
    include_package_data=True,
    python_requires=">=3.5",
    zip_safe=False
)
