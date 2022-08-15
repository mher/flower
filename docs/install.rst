Installation
============

Installing `flower` with `pip <http://www.pip-installer.org/>`_ is simple ::

    $ pip install flower

Development version can be installed with ::

    $ pip install https://github.com/mher/flower/zipball/master#egg=flower

Usage
-----

**Important** Please note that from version 1.0.1 Flower uses Celery 5 and has to be invoked in the same style as celery
commands do.

The key takeaway here is that the Celery app's arguments have to be specified after the `celery` command and Flower's
arguments have to be specified after the `flower` sub-command.

This is the template to follow::

    celery [celery args] flower [flower args]

Core Celery args that you may want to set::

    -A, --app
    -b, --broker
    --result-backend

More info on available `Celery command args <https://docs.celeryq.dev/en/stable/reference/cli.html#celery>`_.

For Flower command args `see here <https://flower.readthedocs.io/en/latest/config.html#options>`_.

Usage Examples
--------------

Launch the Flower server at specified port other than default 5555 (open the UI at http://localhost:5566): ::

    $ celery flower --port=5566

Specify Celery application path with address and port for Flower: ::

    $ celery -A proj flower --address=127.0.0.6 --port=5566

Launch using docker: ::

    $ docker run -p 5555:5555 mher/flower

Launch with unix socket file: ::

    $ celery flower --unix-socket=/tmp/flower.sock

Broker URL and other configuration options can be passed through the standard Celery options (notice that they are after
Celery command and before Flower sub-command): ::

    $ celery --broker=amqp://guest:guest@localhost:5672// flower

