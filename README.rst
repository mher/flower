Flower
======

.. image:: https://github.com/mher/flower/workflows/Build/badge.svg
    :target: https://github.com/mher/flower/actions

.. image:: https://img.shields.io/pypi/v/flower.svg
    :target: https://pypi.python.org/pypi/flower

.. image:: https://travis-ci.org/mher/flower.svg?branch=master
        :target: https://travis-ci.org/mher/flower

Flower is a web based tool for monitoring and administrating Celery clusters.

Features
--------

- Real-time monitoring using Celery Events

    - Task progress and history
    - Ability to show task details (arguments, start time, runtime, and more)
    - Graphs and statistics

- Remote Control

    - View worker status and statistics
    - Shutdown and restart worker instances
    - Control worker pool size and autoscale settings
    - View and modify the queues a worker instance consumes from
    - View currently running tasks
    - View scheduled tasks (ETA/countdown)
    - View reserved and revoked tasks
    - Apply time and rate limits
    - Configuration viewer
    - Revoke or terminate tasks

- Broker monitoring

    - View statistics for all Celery queues
    - Queue length graphs

- HTTP API
- Basic Auth, Google, Github, Gitlab and Okta OAuth
- Prometheus integration

Installation
------------

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

More info on available `Celery command args <https://docs.celeryproject.org/en/stable/reference/cli.html#celery>`_.

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

    $ celery -A proj --broker=amqp://guest:guest@localhost:5672// flower

API
---

Flower API enables to manage the cluster via REST API, call tasks and
receive task events in real-time via WebSockets.

For example you can restart worker's pool by: ::

    $ curl -X POST http://localhost:5555/api/worker/pool/restart/myworker

Or call a task by: ::

    $ curl -X POST -d '{"args":[1,2]}' http://localhost:5555/api/task/async-apply/tasks.add

Or terminate executing task by: ::

    $ curl -X POST -d 'terminate=True' http://localhost:5555/api/task/revoke/8a4da87b-e12b-4547-b89a-e92e4d1f8efd

Or receive task completion events in real-time: ::

    var ws = new WebSocket("ws://localhost:5555/api/task/events/task-succeeded/");
    ws.onmessage = function (event) {
        console.log(event.data);
    }

For more info checkout `API Reference`_ and `examples`_.

.. _API Reference: https://flower.readthedocs.io/en/latest/api.html
.. _examples: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

Documentation
-------------

Documentation is available at `Read the Docs`_ and `IPython Notebook Viewer`_

.. _Read the Docs: https://flower.readthedocs.io
.. _IPython Notebook Viewer: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

License
-------

Flower is licensed under BSD 3-Clause License. See the LICENSE file
in the top distribution directory for the full license text.
