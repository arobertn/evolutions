#!/usr/bin/env python3

from os import path
from setuptools import setup

this_dir = path.abspath(path.dirname(__file__))
try:
    with open(path.join(this_dir, 'README.md')) as f:
        long_desc_content = f.read()
except IOError:
    long_desc_content = ''

setup(name='evolutions',
      description='App framework agnostic pure SQL incremental database migrations tool modeled after play-evolutions',
      long_description=long_desc_content,
      long_description_content_type='text/markdown',
      url="https://github.com/arobertn/evolutions",
      author="Adrian Robert",
      author_email="arobert@interstitiality.net",
      version='0.8.3',
      license='BSD-3-Clause',
      python_requires='>=3',
      platforms=['any'],
      classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Database',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: BSD License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3',
    ],
    keywords='database migration sql python python3 evolutions',
    packages=['evolutions'],
    scripts=['evolutions/evolutions.py'],
    test_suite='evolutions.test.runtests'
)
