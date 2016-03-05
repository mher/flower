========
 flower
========

SYNOPSIS
========

``flower`` [*OPTIONS*]

DESCRIPTION
===========

Flower is a web based tool for monitoring and administrating Celery clusters.
It has these features:

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


OPTIONS
=======

  --address                        run on the given address
  --auth                           regexp  of emails to grant access
  --basic_auth                     colon separated user-password to enable
                                   basic auth
  --broker_api                     inspect broker e.g.
                                   http://guest:guest@localhost:15672/api/
  --certfile                       path to SSL certificate file
  --db                             flower database file (default *flower.db*)
  --debug                          run in debug mode (default *False*)
  --help                           show this help information
  --inspect                        inspect workers (default *True*)
  --inspect_timeout                inspect timeout (in milliseconds) (default
                                   *1000*)
  --keyfile                        path to SSL key file
  --max_workrs                     maximum number of workers to keep in memory
                                   (default *5000*)
  --max_tasks                      maximum number of tasks to keep in memory
                                   (default *10000*)
  --persistent                     enable persistent mode (default *False*)
  --port                           run on the given port (default *5555*)
  --url_prefix                     base url prefix
  --xheaders                       enable support for the 'X-Real-Ip' and
                                   'X-Scheme' headers. (default *False*)

TORNADO OPTIONS
===============

  --log_file_max_size              max size of log files before rollover
                                   (default *100000000*)
  --log_file_num_backups           number of log files to keep (default *10*)
  --log_file_prefix=PATH           Path prefix for log files. Note that if you
                                   are running multiple tornado processes,
                                   log_file_prefix must be different for each
                                   of them (e.g. include the port number)
  --log_to_stderr                  Send log output to stderr (colorized if
                                   possible). By default use stderr if
                                   ``--log_file_prefix`` is not set and no other
                                   logging is configured.
  --logging=debug|info|warning|error|none
                                   Set the Python log level. If *none*, tornado
                                   won't touch the logging configuration.
                                   (default *info*)

USAGE
=====

Launch the server and open http://localhost:5555: ::

    $ flower -A proj --port=5555

Or, launch from Celery: ::

    $ celery flower -A proj --address=127.0.0.1 --port=5555

Broker URL and other configuration options can be passed through the standard Celery options: ::

    $ celery flower -A proj --broker=amqp://guest:guest@localhost:5672//
