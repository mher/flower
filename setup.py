#!/usr/bin/env python
import os
import re

from setuptools import setup, find_packages


version = re.compile(r'VERSION\s*=\s*\((.*?)\)')


def get_package_version():
    "returns package version without importing it"
    base = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(base, "flower/__init__.py")) as initf:
        for line in initf:
            m = version.match(line.strip())
            if not m:
                continue
            return ".".join(m.groups()[0].split(", "))


setup(
    name='flower',
    version=get_package_version(),
    description='Celery Flower',
    long_description=open('README.rst').read(),
    author='Mher Movsisyan',
    url='https://github.com/mher/flower',
    packages=find_packages(),
    install_requires=['celery', 'tornado'],
    package_data={'flower': ['templates/*', 'static/**/*']},
    entry_points={
        'console_scripts': [
            'flower = flower.__main__:main',
        ],
        'celery.commands': [
            'flower = flower.command:Admin',
        ],
    },
)
