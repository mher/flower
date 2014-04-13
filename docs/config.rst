:tocdepth: 2

Configuration
=============

Flower can be configured from the command line: ::

    $ flower --auto_refresh=False

Or, using :file:`flowerconfig.py` configuration file:

.. code-block:: python

    # Broker settings
    BROKER_URL = 'amqp://guest:guest@localhost:5672//'

    # RabbitMQ management api url
    broker_api = 'http://guest:guest@localhost:15672/api/'

    # Enable debug logging
    logging = 'DEBUG'

Options passed via the command line have precedence over the options
defined in the configuration file.

.. note::

    :file:`flowerconfig.py` file should be available on the Python path.

.. _`Celery Configuration reference`: http://docs.celeryproject.org/en/latest/configuration.html#configuration

Options
-------

Flower accepts all standard Celery configuration options: ::

    $ flower --broker_url=amqp://guest:guest@localhost:5672//

See `Celery Configuration reference`_ for a complete listing of all
the available settings, and their default values.

.. contents::
    :local:
    :depth: 2

auto_refresh
~~~~~~~~~~~~

Refresh dashboards automatically (by default, `auto_refresh=True`)

port
~~~~

Run the http server on a given port (by default, `port=5555`)

address
~~~~~~~

Run the http server on a given address

debug
~~~~~

Enable the debug mode (by default, `debug=False`)

max_tasks
~~~~~~~~~

Maximum number of tasks to keep in memory (by default, `max_tasks=10000`)

certfile
~~~~~~~~

A path to SSL certificate file

keyfile
~~~~~~~

A path to SSL key file

