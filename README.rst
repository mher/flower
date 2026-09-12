Flower
======

.. image:: https://img.shields.io/pypi/dm/flower.svg
    :target: https://pypistats.org/packages/flower
    :alt: PyPI - Downloads
.. image:: https://img.shields.io/docker/pulls/mher/flower.svg
    :target: https://hub.docker.com/r/mher/flower
    :alt: Docker Pulls
.. image:: https://github.com/mher/flower/workflows/Build/badge.svg
    :target: https://github.com/mher/flower/actions
.. image:: https://img.shields.io/pypi/v/flower.svg
    :target: https://pypi.python.org/pypi/flower

Flower is an open-source web application for monitoring and managing Celery clusters.
It provides real-time information about the status of Celery workers and tasks.

Features
--------

- Real-time monitoring using Celery Events
    - View task progress and history
    - View task details (arguments, start time, runtime, and more)
- Remote Control
    - View worker status and statistics
    - Shutdown and restart worker instances
    - Control worker pool size and autoscale settings
    - View and modify the queues a worker instance consumes from
    - View currently running tasks
    - View scheduled tasks (ETA/countdown)
    - View reserved and revoked tasks
    - Apply time and rate limits
    - Revoke or terminate tasks
- Broker monitoring
    - View statistics for all Celery queues
- HTTP Basic Auth, Google, Github, Gitlab and Okta OAuth
- Prometheus integration
- API

Installation
------------

Installing `flower` with `pip <http://www.pip-installer.org/>`_ is simple ::

    $ pip install flower

The development version can be installed from Github ::

    $ pip install https://github.com/mher/flower/zipball/master#egg=flower

Usage
-----

To run Flower, you need to provide the broker URL ::

    $ celery --broker=amqp://guest:guest@localhost:5672// flower

Or use the configuration of `celery application <https://docs.celeryq.dev/en/stable/userguide/application.html>`_  ::

    $ celery -A tasks.app flower

By default, flower runs on port 5555, which can be modified with the `port` option ::

    $ celery -A tasks.app flower --port=5001

You can also run Flower using the docker image ::

    $ docker run -v $(pwd)/examples:/data -p 5555:5555 mher/flower celery --app=tasks.app flower

In this example, Flower is using the `tasks.app` defined in the `examples/tasks.py <https://github.com/mher/flower/blob/master/examples/tasks.py>`_ file

API
---

The Flower API lets you manage the cluster over HTTP.

For example you can grow a worker's pool by: ::

    $ curl -X POST -d 'n=1' http://localhost:5555/api/worker/pool/grow/celery@$(hostname)

Or call a task by: ::

    $ curl -X POST -d '{"args":[1,2]}' http://localhost:5555/api/task/async-apply/tasks.add

Or terminate a running task by: ::

    $ curl -X POST -d 'terminate=True' http://localhost:5555/api/task/revoke/8a4da87b-e12b-4547-b89a-e92e4d1f8efd

For more info, see the `API Reference`_

.. _API Reference: https://flower.readthedocs.io/en/latest/api.html

Documentation
-------------

Documentation is available at `Read the Docs`_

.. _Read the Docs: https://flower.readthedocs.io

License
-------

Flower is licensed under BSD 3-Clause License.
See the `License`_ file for the full license text.

.. _`License`: https://github.com/mher/flower/blob/master/LICENSE
