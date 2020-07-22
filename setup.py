#!/usr/bin/env python3

from setuptools import setup, find_namespace_packages

setup(
    name="cocotbext.axi4stream",
    version="1.0",
    author="Nicola Corna",
    author_email="nicola.corna@polimi.it",
    description="Cocotb AXI4-Stream module",
    url="https://github.com/corna/cocotbext.axi4stream.git",
    packages=find_namespace_packages(include=['cocotbext.*']),
    install_requires=['cocotb'],
    python_requires='>=3.5',
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
