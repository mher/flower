Getting started
===============

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

By default, flower runs on port 5555, which can be modified with the :ref:`port` option ::

    $ celery -A tasks.app flower --port=5001

You can also run Flower using the docker image ::

    $ docker run -v examples:/data -p 5555:5555 mher/flower celery --app=tasks.app flower

In this example, Flower is using the `tasks.app` defined in the `examples/tasks.py <https://github.com/mher/flower/blob/master/examples/tasks.py>`_ file
