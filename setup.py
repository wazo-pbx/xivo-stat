#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from setuptools import setup
from setuptools import find_packages

setup(
    name='xivo-stat',
    version='0.1',
    description='XiVO Stat Generation Script',
    author='Avencall',
    author_email='dev@avencall.com',
    url='http://git.xivo.io/',
    license='GPLv3',
    packages=find_packages(),
    scripts=['bin/xivo-stat'],
)
