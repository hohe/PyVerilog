#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='PyVerilog',
      version='0.1',
      description='Verilog Parser for Python',
      url='https://github.com/yellekelyk/PyVerilog',
      author='yellekelyk',
      packages=['PyVerilog'],
      install_requires=[
          'PyYAML',
          'ordereddict',
          'pyparsing',
          'wsgiref',
      ],
      zip_safe=False)
