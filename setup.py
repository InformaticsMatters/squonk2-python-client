#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup module for the Squonk2 Python Client module.
"""

# July 2022

import os
import setuptools

# Pull in the essential run-time requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

# Use the README.rst as the long description.
with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="im-squonk2-client",
    version=os.environ.get("GITHUB_REF_SLUG", "1.0.0"),
    author="Alan Christie",
    author_email="achristie@informaticsmatters.com",
    url="https://github.com/informaticsmatters/squonk2-python-client",
    license="MIT",
    description="Squonk2 Python Client",
    long_description=long_description,
    keywords="api",
    platforms=["any"],
    # Our modules to package
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    include_package_data=True,
    # Project classification:
    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=requirements,
    python_requires=">=3",
    zip_safe=False,
)
