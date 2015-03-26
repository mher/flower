Installation
============

Installing `flower` with `pip <http://www.pip-installer.org/>`_ is simple ::

    $ pip install flower

Or, with `easy_install <http://pypi.python.org/pypi/setuptools>`_ ::

    $ easy_install flower

Usage
-----

Launch the server and open http://localhost:5555: ::

    $ flower -A proj --port=5555

Or, launch from Celery: ::

    $ celery flower -A proj --address=127.0.0.1 --port=5555

Broker URL and other configuration options can be passed through the standard Celery options: ::

    $ celery flower -A proj --broker=amqp://guest:guest@localhost:5672//

