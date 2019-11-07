#! /usr/bin/python
from setuptools import setup

setup(
    name="cocomod-axi4stream",
    use_scm_version={
        "relative_to": __file__,
        "write_to": "cocomod/axi4stream/version.py",
    },
    author="Nicola Corna",
    author_email="nicola.corna@polimi.it",
    description="Cocotb AXI4-Stream module",
    url="https://github.com/corna/cocomod-axi4stream.git",
    packages=["cocomod.axi4stream"],
    install_requires=['cocotb'],
    setup_requires=[
        'setuptools_scm',
    ],
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
