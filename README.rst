Celery Flower
=============

.. image:: https://badge.fury.io/py/flower.png
        :target: http://badge.fury.io/py/flower
.. image:: https://travis-ci.org/mher/flower.png?branch=master
        :target: https://travis-ci.org/mher/flower
.. image:: https://pypip.in/d/flower/badge.png
        :target: https://crate.io/packages/flower/
.. image:: https://d2weczhvl823v0.cloudfront.net/mher/flower/trend.png
   :alt: Bitdeli badge
   :target: https://bitdeli.com/free

Flower is a web based tool for monitoring and administrating Celery clusters.

.. include:: docs/features.rst

API
---

Flower API enables to manage the cluster via REST api, call tasks and receive task
events in real-time via WebSockets.

For example you can restart worker's pool by: ::

    $ curl -X POST http://localhost:5555/api/worker/pool/restart/myworker

Or call a task by: ::

    $ curl -X POST -d '{"args":[1,2]}' http://localhost:5555/api/task/async-apply/tasks.add

Or terminate executing task by: ::

    $ curl -X POST -d 'terminate=True' http://localhost:5555/api/task/revoke/8a4da87b-e12b-4547-b89a-e92e4d1f8efd

Or receive task completion events in real-time: ::

    var ws = new WebSocket('ws://localhost:5555/api/task/events/task-succeeded/');
    ws.onmessage = function (event) {
        console.log(event.data);
    }


See detailed API documentation here_.

.. _here: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

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

Documentation
-------------

Documentation is available at `Github Wiki`_ and `IPython Notebook Viewer`_

.. _Github Wiki: https://github.com/mher/flower/wiki
.. _IPython Notebook Viewer: http://nbviewer.ipython.org/urls/raw.github.com/mher/flower/master/docs/api.ipynb

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

Contributing
------------

If you'd like to contribute, simply fork `the repository`_, commit your
changes, run the tests (`python -m tests`) and send a pull request.
Make sure you add yourself to AUTHORS_.

.. _`the repository`: https://github.com/mher/flower
.. _AUTHORS: https://github.com/mher/flower/blob/master/AUTHORS
