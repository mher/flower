#!/usr/bin/env python
import os
import re

from setuptools import setup, find_packages


version = re.compile(r'VERSION\s*=\s*\((.*?)\)')


def get_package_version():
    "returns package version without importing it"
    base = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(base, "celeryadmin/__init__.py")) as initf:
        for line in initf:
            m = version.match(line.strip())
            if not m:
                continue
            return ".".join(m.groups()[0].split(", "))


setup(
    name='celeryadmin',
    version=get_package_version(),
    description='Celery Web Admin',
    long_description=open('README.rst').read(),
    author='Mher Movsisyan',
    url='https://github.com/mher/celery-admin',
    packages=find_packages(),
    install_requires=['celery', 'tornado'],
    package_data={'celeryadmin': ['templates/*', 'static/**/*']},
    entry_points={
        'console_scripts': [
            'celeryadmin = celeryadmin.__main__:main',
        ]
    },
)
