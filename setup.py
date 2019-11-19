#!/usr/bin/env python3

from setuptools import setup

setup(name='evolutions',
      description='Database migrations',
      long_description='Tool for managing relational database schema evolution and data migration, modeled on the Scala/Java play-evolutions library.  Minimalist approach supporting only linear history and pure SQL migrations that works and stays out of your way in development and production environments.',
      url="https://github.com/arobertn/evolutions",
      author="Adrian Robert",
      author_email="arobert@interstitiality.net",
      version='0.8',
      license='BSD-3-Clause',
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
