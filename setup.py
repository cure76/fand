#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from setuptools import setup, find_packages
from fand import __version__


setup(
    name="fand",
    version=__version__,
    description="CPU temperature monitor {0}".format(__version__),
    author="Vladimir Gusenkov",
    author_email="gusenkovvladimir@yandex.ru",
    license='BSD',
    install_requires=[
        'gpiozero>=1.5',
        # Optional, improves asyncio performance if present
        # Users on non-asyncio platforms can skip it
        'uvloop>=0.17; platform_system!="Windows"'
    ],
    packages=find_packages(),
    scripts=['fand.py'],
    data_files=[
        ('share/fand/', ['fand.service']),
    ],
    platforms="any",
    python_requires='>=3.8'
)
