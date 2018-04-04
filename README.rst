Celery Flower
=============

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
- Basic Auth and Google OpenID authentication

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

Or receive task completion events in real-time:

.. code-block:: javascript 

    var ws = new WebSocket('ws://localhost:5555/api/task/events/task-succeeded/');
    ws.onmessage = function (event) {
        console.log(event.data);
    }

For more info checkout `API Reference`_ and `examples`_.

.. _API Reference: https://flower.readthedocs.io/en/latest/api.html
.. _examples: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

Installation
------------

PyPI version: ::

    $ pip install flower

Development version: ::

    $ pip install https://github.com/mher/flower/zipball/master

Usage
-----

Launch the server and open http://localhost:5555: ::

    $ flower --port=5555

Or launch from celery: ::

    $ celery flower -A proj --address=127.0.0.1 --port=5555

Broker URL and other configuration options can be passed through the standard Celery options: ::

    $ celery flower -A proj --broker=amqp://guest:guest@localhost:5672//

Or run with unix socket file: ::

    $ flower --unix_socket=/tmp/flower.sock


Documentation
-------------

Documentation is available at `Read the Docs`_ and `IPython Notebook Viewer`_

.. _Read the Docs: https://flower.readthedocs.io
.. _IPython Notebook Viewer: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

License
-------

Flower is licensed under BSD 3-Clause License. See the LICENSE file
in the top distribution directory for the full license text.

Getting help
------------

Please head over to #celery IRC channel on irc.freenode.net or
`open an issue`_.

.. _open an issue: https://github.com/mher/flower/issues

Contributing
------------

If you'd like to contribute, simply fork `the repository`_, commit your
changes, run the tests (`tox`) and send a pull request.
Make sure you add yourself to CONTRIBUTORS_.

If you are interested in maintaining the project please contact.

.. _`the repository`: https://github.com/mher/flower
.. _CONTRIBUTORS: https://github.com/mher/flower/blob/master/CONTRIBUTORS
