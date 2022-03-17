:tocdepth: 2

Configuration
=============

Flower can be configured from the command line: ::

    $ celery flower --auto_refresh=False

Using :file:`flowerconfig.py` configuration file:

.. code-block:: python

    # RabbitMQ management api
    broker_api = 'http://guest:guest@localhost:15672/api/'

    # Enable debug logging
    logging = 'DEBUG'

Or, using the environment variables. All flower options should be
prefixed with `FLOWER_`::

    $ export FLOWER_BASIC_AUTH=foo:bar

Options passed through the command line have precedence over the options
defined in the configuration file. The configuration file name and path
can be changed with `conf`_ option. ::

    $ celery flower --conf=celeryconfig.py

Options
-------

Standard Celery configuration settings can be overridden in the configuration
file. See `Celery Configuration reference`_ for a complete listing of all
the available settings, and their default values.

.. _`Celery Configuration reference`: https://docs.celeryq.dev/en/latest/userguide/configuration.html

Celery command line options also can be passed to Flower. For example
the `--broker` sets the default broker URL: ::

    $ celery -A proj --broker=amqp://guest:guest@localhost:5672// flower

For a full list of options see: ::

    $ celery --help

.. contents::
    :local:
    :depth: 1

.. _address:

address
~~~~~~~

Run the http server on a given address. Address may be either an IP address or hostname.
If it’s a hostname, the server will listen on all IP addresses associated with the name.
Address may be an empty string or None to listen on all available interfaces.

.. _auth:

auth
~~~~

Enables authentication. `auth` is a regexp of emails to grant access.
For more info see :ref:`authentication`.

.. _auto_refresh:

auto_refresh
~~~~~~~~~~~~

Refresh dashboards automatically (by default, `auto_refresh=True`)

.. _basic_auth:

basic_auth
~~~~~~~~~~

Enables HTTP Basic authentication. `basic_auth` is a comma separated list
of `username:password`. See :ref:`basic-auth` for more info.

.. _broker_api:

broker_api
~~~~~~~~~~

Flower uses `RabbitMQ Management Plugin`_ to get info about queues.
`broker_api` is a URL of RabbitMQ HTTP API including user credentials. ::

    $ celery -A proj flower --broker_api=http://username:password@rabbitmq-server-name:15672/api/

.. Note:: By default the management plugin is not enabled. To enable it run::

    $ rabbitmq-plugins enable rabbitmq_management

.. Note:: The port number for RabbitMQ versions prior to 3.0 is 55672.

.. _`RabbitMQ Management Plugin`: https://www.rabbitmq.com/management.html

.. _ca_certs:

ca_certs
~~~~~~~~

A path to `ca_certs` file. The `ca_certs` file contains a set of concatenated “certification authority”
certificates, which are used to validate certificates passed from the other end of the connection.
For more info see `Python SSL`_

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

Sets worker inspect timeout (by default, `inspect_timeout=1000`
in milliseconds)

.. _keyfile:

keyfile
~~~~~~~

A path to SSL key file

.. _max_workers:

max_workers
~~~~~~~~~~~

Maximum number of workers to keep in memory (by default, `max_workers=5000`)

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

.. _state_save_interval:

state_save_interval
~~~~~~~~~~~~~~~~~~

Sets the interval for saving state. state_save_interval=0 means
that periodic saving is disabled (by default, `state_save_interval=0`
in milliseconds)

.. _xheaders:

xheaders
~~~~~~~~

Enable support of `X-Real-Ip` and `X-Scheme` headers
(by default, `xheaders=False`)

.. _tasks_columns:

tasks_columns
~~~~~~~~~~~~~

Specifies list of comma-delimited columns on `/tasks/` page. `all` value
enables all columns. Columns on the page can be reordered using drag and drop.

(by default, `tasks_columns="name,uuid,state,args,kwargs,result,received,started,runtime,worker"`)

Available columns are:

  - `name`
  - `uuid`
  - `state`
  - `args`
  - `kwargs`
  - `result`
  - `received`
  - `started`
  - `runtime`
  - `worker`
  - `retries`
  - `revoked`
  - `exception`
  - `expires`
  - `eta`

.. _url_prefix:

url_prefix
~~~~~~~~~~

Enables deploying Flower on non-root URL

For example to access Flower on http://example.com/flower run it with: ::

    $ celery flower --url_prefix=flower

NOTE: The old `nginx` rewrite is no longer needed


.. _unix_socket:

unix_socket
~~~~~~~~~~~

Run flower using UNIX socket file

.. _cookie_secret:

cookie_secret
~~~~~~~~~~~~~

Set a secret key for signing cookies

.. _auth_provider:

auth_provider
~~~~~~~~~~~~~

Sets authentication provider

  - Google `flower.views.auth.GoogleAuth2LoginHandler`
  - GitHub `flower.views.auth.GithubLoginHandler`
  - GitLab `flower.views.auth.GitLabLoginHandler`

See `Authentication` for usage examples

.. _purge_offline_workers:

purge_offline_workers
~~~~~~~~~~~~~~~~~~~~~

Time (in seconds) after which offline workers are automatically removed from dashboard.

If omitted, offline workers remain on the dashboard.

.. _task_runtime_metric_buckets:

task_runtime_metric_buckets
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sets task runtime latency buckets

buckets value can be provided as cli options: ::

    $ celery flower --task_runtime_metric_buckets=1,5,10,inf

Or, it can be also provided as ENV variable: ::

    $ export FLOWER_TASK_RUNTIME_METRIC_BUCKETS=1,5,10,inf

If not provided:
    - default prometheus buckets will be used
