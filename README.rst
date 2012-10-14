Celery Flower
=============

Flower is a web based tool for monitoring and administrating Celery clusters.

Features
--------

* Shutdown or restart workers
* View workers status (completed, running tasks, etc.)
* View worker pool options (timeouts, processes, etc.)
* Control worker pool size
* View message broker options
* View active queues, add or cancel queues
* View processed task stats by type
* View currently running tasks
* View scheduled tasks
* View reserved and revoked tasks
* Apply time and rate limits
* View all active configuration options
* View all tasks (by type, by worker, etc.)
* View all task options (arguments, start time, runtime, etc.)
* Revoke or terminate tasks
* View real-time execution graphs
* Google OpenID authentication

API
---

Flower API enables to control the cluster via REST api and receive task
events in real-time via WebSockets.

For example you can restart worker's pool by: ::

    $ curl -X POST http://localhost:5555/api/worker/pool/restart/myworker

Or terminate executing task by: ::

    $ curl -X POST -d '{"terminate":True}' http://localhost:5555/api/task/revoke/8a4da87b-e12b-4547-b89a-e92e4d1f8efd

Or receive task completion events in real-time: ::

    var ws = new WebSocket('ws://localhost:5555/api/task/events/task-succeeded/');
    ws.onmessage = function (event) {
        console.log(event.data);
    }

Installation
------------

To install, simply: ::

    $ pip install flower

Usage
-----

Launch the server and open http://localhost:5555: ::

    $ flower --port=5555

Or launch from celery: ::

    $ celery flower --address=127.0.0.1 --port=5555

Broker URL and other configuration options can be passed through the standard Celery options: ::

    $ celery flower --broker=amqp://guest:guest@localhost:5672//

Screenshots
-----------

.. image:: https://raw.github.com/mher/flower/master/docs/screenshots/dashboard.png
   :width: 800px

.. image:: https://raw.github.com/mher/flower/master/docs/screenshots/pool.png
   :width: 800px

.. image:: https://raw.github.com/mher/flower/master/docs/screenshots/tasks.png
   :width: 800px

.. image:: https://raw.github.com/mher/flower/master/docs/screenshots/task.png
   :width: 800px

.. image:: https://raw.github.com/mher/flower/master/docs/screenshots/monitor.png
   :width: 800px

More screenshots_

.. _screenshots: https://github.com/mher/flower/tree/master/docs/screenshots

Getting help
------------

Please head over to #celery IRC channel on irc.freenode.net or
`open an issue`_.

.. _open an issue: https://github.com/mher/flower/issues
