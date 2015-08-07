:tocdepth: 2

Configuration
=============

Flower can be configured from the command line: ::

    $ flower --auto_refresh=False

Using :file:`flowerconfig.py` configuration file:

.. code-block:: python

    # Broker settings
    BROKER_URL = 'amqp://guest:guest@localhost:5672//'

    # RabbitMQ management api
    broker_api = 'http://guest:guest@localhost:15672/api/'

    # Enable debug logging
    logging = 'DEBUG'

Or, using the environment variables. All flower options should be
prefixed with `FLOWER_`::

    $ export FLOWER_BASIC_AUTH=foo:bar

Options passed through the command line have precedence over the options
defined in the configuration file. The configuration file name and path
can be changed with `conf`_ option.

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

.. _address:

address
~~~~~~~

Run the http server on a given address

.. _auth:

auth
~~~~

Enables Google OpenID authentication. `auth` is a regexp of emails
to grant access. For more info see :ref:`google-openid`

.. _auto_refresh:

auto_refresh
~~~~~~~~~~~~

Refresh dashboards automatically (by default, `auto_refresh=True`)

.. _basic_auth:

basic_auth
~~~~~~~~~~

Enables HTTP Basic authentication. `basic_auth` is a comma separated list
of `username:passworrd`. See :ref:`basic-auth` for more info.

.. _broker_api:

broker_api
~~~~~~~~~~

Flower uses `RabbitMQ Managment Plugin`_ to get info about queues.
`broker_api` is a URL of RabbitMQ HTTP API including user credentials. ::

    $ flower -A proj --broker_api=http://username:password@rabbitmq-server-name:15672/api/

.. Note:: By default the managment plugin is not enabled. To enable it run::

    $ rabbitmq-plugins enable rabbitmq_management

.. Note:: The port number for RabbitMQ versions prior to 3.0 is 55672.

.. _`RabbitMQ Managment Plugin`: https://www.rabbitmq.com/management.html

.. _ca_certs:

ca_certs
~~~~~~~~

A path to `ca_certs` file. The `ca_certs` file contains a set of concatenated “certification authority”
certificates, which are used to validate certificates passed from the other end of the connection.
For more info see :ref:`Python SSL`_

.. _`Python SSL`: https://docs.python.org/3.4/library/ssl.html

.. _certfile:

certfile
~~~~~~~~

A path to SSL certificate file

.. _conf:

conf
~~~~

A path to the configuration file (by default, :file:`flowerconfig.py`)

.. _db:

db
~~

A database file to use if persistent mode is enabled
(by default, `db=flower`)

.. _debug:

debug
~~~~~

Enable the debug mode (by default, `debug=False`)

.. _enable_events:

enable_events
~~~~~~~~~~~~~

Periodically enable Celery events by using `enable_events` command
(by default, `enable_event=True`)

.. _format_task:

format_task
~~~~~~~~~~~

Modifies the default task formatting. `format_task` function should be
defined in the `flowerconfig.py` configuration file. It accepts a task
object and returns the modified version.

`format_task` is useful for filtering out sensitive information.

The example below shows how to filter arguments and limit display lengths:

.. code-block:: python

    from flower.utils.template import humanize

    def format_task(task):
        task.args = humanize(task.args, length=10)
        task.kwargs.pop('credit_card_number')
        task.result = humanize(task.result, length=20)
        return task

.. _inspect_timeout:

inspect_timeout
~~~~~~~~~~~~~~~

Sets worker inspect timeout (by default, `inspect_timeout=10000`
in milliseconds)

.. _keyfile:

keyfile
~~~~~~~

A path to SSL key file

.. _max_tasks:

max_tasks
~~~~~~~~~

Maximum number of tasks to keep in memory (by default, `max_tasks=10000`)

.. _natural_time:

natural_time
~~~~~~~~~~~~

Show time relative to the refresh time (by default, `natural_time=True`)

.. _persistent:

persistent
~~~~~~~~~~

Enable persistent mode. If the persistent mode is enabled Flower saves
the current state and reloads on restart (by default, `persistent=False`)

.. _port:

port
~~~~

Run the http server on a given port (by default, `port=5555`)

.. _xheaders:

xheaders
~~~~~~~~

Enable support of `X-Real-Ip` and `X-Scheme` headers
(by default, `xheaders=False`)

tasks_columns
~~~~~~~~~~~~~

Specifies list of comma-delimited columns on /tasks/ page.
Order of slugs in the option is unrelated to order of columns on the page.
Available slugs: `name`, `uuid`, `state`, `args`, `kwargs`,
`result`, `received`, `started`, `runtime`
