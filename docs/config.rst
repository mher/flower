:tocdepth: 2

Configuration
=============

Flower can be configured from the command line: ::

    $ flower --auto_refresh=False

Or, using :file:`flowerconfig.py` configuration file:

.. code-block:: python

    # Broker settings
    BROKER_URL = 'amqp://guest:guest@localhost:5672//'

    # RabbitMQ management api
    broker_api = 'http://guest:guest@localhost:15672/api/'

    # Enable debug logging
    logging = 'DEBUG'

Options passed through the command line have precedence over the options
defined in the configuration file.

.. note::

    :file:`flowerconfig.py` file should be available on the Python path.


Options
-------

Standard Celery configuration settings can be overridden in the configuration
file. See `Celery Configuration reference`_ for a complete listing of all
the available settings, and their default values.

.. _`Celery Configuration reference`: http://docs.celeryproject.org/en/latest/configuration.html#configuration

Celery command line options also can be passed to Flower. For example
the `--broker` sets the default broker url: ::

    $ flower -A proj --broker=amqp://guest:guest@localhost:5672//

For a full list of options see: ::

    $ celery --help

.. contents::
    :local:
    :depth: 1

address
~~~~~~~

Run the http server on a given address

auth
~~~~

Enables Google OpenID authentication. `auth` is a regexp of emails
to grant access. For more info see :ref:`google-openid`

auto_refresh
~~~~~~~~~~~~

Refresh dashboards automatically (by default, `auto_refresh=True`)

basic_auth
~~~~~~~~~~

Enables HTTP Basic authentication. `basic_auth` is a comma separated list
of `username:passworrd`. See :ref:`basic-auth` for more info.

broker_api
~~~~~~~~~~

Flower uses `RabbitMQ Managment Plugin`_ to get info about queues.
`broker_api` is a URL of RabbitMQ HTTP API including user credentials. ::

    $ flower -A proj --broker_api=http://username:password@rabbitmq-server-name:15672/api/

.. Note:: By default the managment plugin is not enabled. To enable it run::

    $ rabbitmq-plugins enable rabbitmq_management

.. _`RabbitMQ Managment Plugin`: https://www.rabbitmq.com/management.html

certfile
~~~~~~~~

A path to SSL certificate file

db
~~

A database file to use if persistent mode is enabled
(by default, `db=flower`)

debug
~~~~~

Enable the debug mode (by default, `debug=False`)

inspect
~~~~~~~

Enable inspecting running workers (by default, `inspect=True`).

inspect_timeout
~~~~~~~~~~~~~~~

Sets worker inspect timeout (by default, `inspect_timeout=10000`
in milliseconds)

keyfile
~~~~~~~

A path to SSL key file

max_tasks
~~~~~~~~~

Maximum number of tasks to keep in memory (by default, `max_tasks=10000`)

persistent
~~~~~~~~~~

Enable persistent mode. If the persistent mode is enabled Flower saves
the current state and reloads on restart (by default, `persistent=False`)

port
~~~~

Run the http server on a given port (by default, `port=5555`)

url_prefix
~~~~~~~~~~

Enables deploying Flower on non-root URL.

For example to access Flower on http://example.com/flower run it with: ::

    $ flower -A proj --url_prefix=flower

And use the following `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name example.com;

        location /flower/ {
            rewrite ^/flower/(.*)$ /$1 break;
            proxy_pass http://example.com:5555;
            proxy_set_header Host $host;
        }

    }

xheaders
~~~~~~~~

Enable support of `X-Real-Ip` and `X-Scheme` headers
(by default, `xheaders=False`)

