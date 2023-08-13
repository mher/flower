:tocdepth: 2

Configuration
=============

Flower is highly customizable. You can pass configuration options through the command line,
configuration file, or environment variables. For a full list of options, see the `Option Reference`_ section.

Command line
------------

Flower operates as a sub-command of Celery, allowing you to pass both Celery and Flower
configuration options from the command line. The template for this is as follows ::

    celery [celery options] flower [flower options]

Celery options should be specified after the celery command, while Flower options
should be specified after the flower sub-command.

For example ::

    $ celery --broker=redis:// flower --unix-socket=/tmp/flower.sock

See `Celery Configuration reference`_ for a comprehensive listing of all available settings
and their default values.

.. _`Celery Configuration reference`: https://docs.celeryq.dev/en/latest/userguide/configuration.html

Configuration file
------------------

Flower tries to load configuration from the :file:`flowerconfig.py` file by default.
You can override the name of the configuration file with the `conf`_ option.
The configuration file is a simple Python file that contains key-value pairs:

.. code-block:: python

    # Set RabbitMQ management api
    broker_api = 'http://guest:guest@localhost:15672/api/'

    # Enable debug logging
    logging = 'DEBUG'

Environment variables
---------------------

Flower configuration options can also be passed through environment variables.
All Flower options must be prefixed with `FLOWER_`.
For example, to set the basic_auth option to foo:bar, you would set the
`FLOWER_BASIC_AUTH` environment variable to `foo:bar` ::

    export FLOWER_BASIC_AUTH=foo:bar
    celery flower

.. _options_referance:

Option Reference
-----------------

.. contents::
    :local:
    :depth: 1

.. _address:

address
~~~~~~~

Default: '' (empty string)

Sets the address on which the Flower HTTP server should listen.
The address may be either an IP address or a hostname. If a hostname is provided,
the server will listen on all IP addresses associated with that name.
To listen on all available interfaces, set the address to an empty string.

Example:

Listen on all available interfaces::

    $ celery flower --address='0.0.0.0'

Listen only on the loopback interface::

    $ celery flower --address='localhost'

Listen on all IP addresses associated with 'example.com'::

    $ celery flower --address='example.com'


.. _auth:

auth
~~~~

Default: '' (empty string)

Enables authentication. `auth` is a regular expression of emails to grant access.

The `auth` option allows you to enable authentication in Flower. By default, the `auth` option is set to an empty string, indicating that authentication is disabled.

To enable authentication and restrict access to specific email addresses, set the `auth` option to a regular expression pattern that matches the desired email addresses. The `auth` option supports a basic regex syntax, including:

  - Single email: Use a single email address, such as `user@example.com`.
  - Wildcard: Use a wildcard pattern with `.*` to match multiple email addresses with the same domain, such as `.*@example.com`.
  - List of emails: Use a list of emails separated by pipes (`|`), such as `one@example.com|two@example.com`.

Please note that for security reasons, the `auth` option only supports a basic regex syntax and does not provide advanced regex features.

For more information and detailed usage examples, refer to the :ref:`Authentication` section of the Flower documentation.

.. _auto_refresh:

auto_refresh
~~~~~~~~~~~~

Default: True

Enables automatic refresh for the Workers view.
By default, the Workers view automatically refreshes at regular intervals to provide up-to-date
information about the workers. Set this option to `False` to disable automatic refreshing.

.. _basic_auth:

basic_auth
~~~~~~~~~~

Default: None

Enables HTTP Basic authentication. It accepts a comma-separated list of `username:password` pairs.
Each pair represents a valid username and password combination for authentication.

Example:

Enable HTTP Basic authentication with multiple users::

    $ celery flower --basic-auth="user1:password1,user2:password2"

See :ref:`basic-authentication` for more information.

.. _broker_api:

broker_api
~~~~~~~~~~

Default: None

The URL of the broker API used by Flower to retrieve information about queues.

Flower uses the RabbitMQ Management Plugin to gather information about queues.
The `broker_api` option should be set to the URL of the RabbitMQ HTTP API, including user credentials if required.

Example::

    $ celery flower broker-api="http://username:password@rabbitmq-server-name:15672/api/"

.. Note:: By default, the RabbitMQ Management Plugin is not enabled. To enable it, run the following command::

    $ rabbitmq-plugins enable rabbitmq_management

.. Note:: The port number for RabbitMQ versions prior to 3.0 is 55672.

For more information refer to the `RabbitMQ Management Plugin`_ documentation.

.. _`RabbitMQ Management Plugin`: https://www.rabbitmq.com/management.html

.. _ca_certs:

ca_certs
~~~~~~~~

Default: None

Sets the path to the `ca_certs` file containing a set of concatenated "certification authority" certificates.

The `ca_certs` file is used to validate certificates received from the other end of the connection.
It contains a collection of trusted root certificates. Set the `ca_certs` option to the path of the `ca_certs` file.
If not specified, certificate validation will not be performed.

For more information about certificate validation in Python, refer to the `Python SSL`_ documentation.

.. _`Python SSL`: https://docs.python.org/3/library/ssl.html

.. _certfile:

certfile
~~~~~~~~

Default: None

Sets the path to the SSL certificate file.

The `certfile` option specifies the path to the SSL certificate file used for SSL/TLS encryption.
The certificate file contains the public key certificate for the Flower server.
If not specified, SSL/TLS encryption will not be used.

.. _conf:

conf
~~~~

Default: flowerconfig.py

Sets the configuration file to be used by Flower.

Example::

    $ celery flower --conf="./examples/celeryconfig.py"

.. _db:

db
~~

Default: flower

Sets the database file to use if persistent mode is enabled.

If the `persistent`_ mode is enabled, the `db` option specifies the database file
to be used by Flower for storing task results, events, or other persistent data.

Example::

    $ celery flower persistent=True --db ="flower_db"

.. _debug:

debug
~~~~~

Default: False

Enables the debug mode

.. Note:: When debug mode is enabled, Flower may print sensitive information

.. _enable_events:

enable_events
~~~~~~~~~~~~~

Default: True

When enabled, Flower periodically sends Celery `enable_events` commands to all workers.
Enabling Celery events allows Flower to receive real-time updates about task events
from the Celery workers.

You can also enable events directly when running Celery workers by using the `-E` flag.
For more information, refer to the `Celery documentation <https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-E>`_:

.. _format_task:

format_task
~~~~~~~~~~~

Default: None

Modifies the default task formatting.

The `format_task` function allows to modify the default formatting of tasks.
By defining the `format_task` function in the `flowerconfig.py` configuration file,
you can customize the task object before it is displayed. The `format_task` function accepts a task object
as a parameter and should return the modified version of the task.

This function is particularly useful for filtering out sensitive information or limiting display lengths of task arguments, kwargs, or results.

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

Default: 1000

Sets the timeout for the worker inspect commands in milliseconds.

Worker inspection involves retrieving information about the workers, such as their current status, tasks, and resource usage.

.. _keyfile:

keyfile
~~~~~~~

Default: None

Sets the path to the SSL key file.

The key file contains the private key corresponding to the SSL certificate.
If not specified, or set to `None`, SSL/TLS encryption will not be used.

.. _max_workers:

max_workers
~~~~~~~~~~~

Default: 5000

Sets the maximum number of workers to keep in memory

.. _max_tasks:

max_tasks
~~~~~~~~~

Default: 100000

Sets the maximum number of tasks to keep in memory

.. _natural_time:

natural_time
~~~~~~~~~~~~

Default: False

Enables showing time relative to the page refresh time in a more human-readable format.

When enabled, timestamps will be shown as relative time such as "2 minutes ago" or "1 hour ago" instead of the exact timestamp.

.. _persistent:

persistent
~~~~~~~~~~

Default: False

Enables persistent mode in Flower.

When persistent mode is enabled, Flower saves its current state and reloads it upon restart.
This ensures that Flower retains its state and configuration across restarts.
Flower stores its state in a database file specified by the `db`_ option.

.. _port:

port
~~~~

Default: 5555

Sets the port number for running the Flower HTTP server.

.. _state_save_interval:

state_save_interval
~~~~~~~~~~~~~~~~~~~

Default: 0

Sets the interval for saving the Flower state.

Flower state includes information about workers, tasks. The state is saved periodically to ensure data persistence and recovery upon restart.

By default, periodic saving is disabled. Flower will not automatically save its state at regular intervals.
If you want to enable periodic state saving, set the `state_save_interval` option to a positive integer value representing the interval in milliseconds.

.. _xheaders:

xheaders
~~~~~~~~

Default: False

Enables support for `X-Real-Ip` and `X-Scheme` headers.

The `xheaders` option allows Flower to enable support for `X-Real-Ip` and `X-Scheme` headers.
These headers are commonly used in proxy or load balancer configurations to preserve the original client IP address and scheme.

.. _tasks_columns:

tasks_columns
~~~~~~~~~~~~~

Default: name,uuid,state,args,kwargs,result,received,started,runtime,worker

Specifies the list of comma-delimited columns to display on the `/tasks` page.

The `tasks_columns` option allows you to customize the columns displayed on the `/tasks` page in Flower.
By default, the specified columns are: name, uuid, state, args, kwargs, result, received, started, runtime, and worker.

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

Example::

    $ celery flower --tasks-columns='name,uuid,state,args,kwargs,result,received,started,runtime,worker,retries,revoked,exception,expires,eta'

In the above example, all available columns are displayed.

.. _url_prefix:

url_prefix
~~~~~~~~~~

Default: '' (empty string)

Enables deploying Flower on a non-root URL.

The `url_prefix` option allows you to deploy Flower on a non-root URL.
By default, Flower is deployed on the root URL. However, if you need to run Flower on a specific path,
such as `http://example.com/flower`, you can specify the desired URL prefix using the `url_prefix` option.

.. _unix_socket:

unix_socket
~~~~~~~~~~~

Default: '' (empty string)

Runs Flower using a UNIX socket file.

The `unix_socket` option allows you to run Flower using a UNIX socket file instead of a network port.
By default, the `unix_socket` option is set to an empty string, indicating that Flower should not use a UNIX socket.

To run Flower using a UNIX socket file, set the `unix_socket` option to the desired path of the UNIX socket file.
Flower will then bind to the specified socket file instead of a network port.

Example::

    $ celery flower --unix-socket='/var/run/flower.sock'

.. _cookie_secret:

cookie_secret
~~~~~~~~~~~~~

Default: token_urlsafe(64) (random string)

Sets a secret key for signing cookies.

The `cookie_secret` option allows you to set a secret key used for signing cookies in Flower.

By default, the `cookie_secret` option is set to 'token_urlsafe(64)', which generates a random string of length 64 characters as the secret key.
This provides a good level of security for signing cookies. If you want to specify a custom secret key, you can set the `cookie_secret` option to the desired string.

.. _auth_provider:

auth_provider
~~~~~~~~~~~~~

Default: None

Sets the authentication provider for Flower.

The `auth_provider` option allows you to set the authentication provider for Flower.
By default, the `auth_provider` option is set to `None`, indicating that no authentication provider is configured.

To enable authentication and specify an authentication provider, set the `auth_provider` option to one of the following values:

  - Google `flower.views.auth.GoogleAuth2LoginHandler`
  - GitHub `flower.views.auth.GithubLoginHandler`
  - GitLab `flower.views.auth.GitLabLoginHandler`
  - Okta `flower.views.auth.OktaLoginHandler`

See also :ref:`Authentication` for usage examples

.. _purge_offline_workers:

purge_offline_workers
~~~~~~~~~~~~~~~~~~~~~

Default: None

Time (in seconds) after which offline workers are automatically removed from the Workers view.
By default, offline workers will remain on the dashboard indefinitely.

.. _task_runtime_metric_buckets:

task_runtime_metric_buckets
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Default: 'Histogram.DEFAULT_BUCKETS' (default prometheus buckets)

Sets the task runtime latency buckets.

You can provide the `buckets` value as a comma-separated list of values.

Example::

    $ celery flower --task-runtime-metric-buckets=1,5,10,inf

The buckets represent the upper bounds of the latency intervals.
You can specify them as integer or float values. The `inf` value represents positive infinity, indicating
that the last bucket captures all values greater than or equal to the previous bucket.

.. _oauth2_key:

oauth2_key
~~~~~~~~~~

Default: None

Sets the OAuth 2.0 key (client ID) issued by the OAuth 2.0 provider

`oauth2_key` option should be used with :ref:`auth`, :ref:`auth_provider`, :ref:`oauth2_redirect_uri` and :ref:`oauth2_secret` options.

.. _oauth2_secret:

oauth2_secret
~~~~~~~~~~~~~

Default: None

Sets the OAuth 2.0 secret issued by the OAuth 2.0 provider

`oauth2_secret` option should be used with :ref:`auth`, :ref:`auth_provider`, :ref:`oauth2_redirect_uri` and :ref:`oauth2_key` options.

.. _oauth2_redirect_uri:

oauth2_redirect_uri
~~~~~~~~~~~~~~~~~~~

Default: None

Sets the URI to which an OAuth 2.0 server redirects the user after successful authentication and authorization.

`oauth2_redirect_uri` option should be used with :ref:`auth`, :ref:`auth_provider`, :ref:`oauth2_key` and :ref:`oauth2_secret` options.
