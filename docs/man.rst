:orphan:

========
 flower
========

SYNOPSIS
========

``flower`` [*OPTIONS*]

DESCRIPTION
===========

Flower is a web-based tool for monitoring and administrating Celery clusters.
It has these features:

.. include:: ../README.rst
   :start-after: .. features-start
   :end-before: .. features-end


OPTIONS
=======

  --address                        run on the given address
  --auth                           regexp of emails to grant access
  --auth-provider                  sets authentication provider class
  --auto-refresh                   refresh workers automatically (default *True*)
  --basic-auth                     colon-separated user-password to enable
                                   basic auth
  --broker-api                     inspect broker e.g.
                                   http://guest:guest@localhost:15672/api/
  --ca-certs                       path to SSL certificate authority (CA) file
  --certfile                       path to SSL certificate file
  --conf                           flower configuration file path (default *flowerconfig.py*)
  --cookie-secret                  secure cookie secret
  --db                             flower database file (default *flower*)
  --debug                          run in debug mode (default *False*)
  --enable-events                  periodically enable Celery events (default *True*)
  --format-task                    use custom task formatter
  --help                           show this help information
  --inspect-timeout                inspect timeout (in milliseconds) (default
                                   *1000*)
  --keyfile                        path to SSL key file
  --max-workers                    maximum number of workers to keep in memory
                                   (default *5000*)
  --max-tasks                      maximum number of tasks to keep in memory
                                   (default *100000*)
  --natural-time                   show time in relative format (default *False*)
  --oauth2-key                     OAuth2 key (client ID) (requires --auth)
  --oauth2-secret                  OAuth2 secret (requires --auth)
  --oauth2-redirect-uri            OAuth2 redirect uri (requires --auth)
  --persistent                     enable persistent mode (default *False*)
  --port                           run on the given port (default *5555*)
  --purge-offline-workers          time (in seconds) after which offline workers are purged
                                   from workers
  --read-only                      enable read only mode, disabling all control
                                   operations (default *False*)
  --state-save-interval            state save interval (in milliseconds) (default *0*)
  --task-runtime-metric-buckets    task runtime prometheus latency metric buckets (default prometheus latency buckets)
  --tasks-columns                  slugs of columns on /tasks/ page in display order,
                                   delimited by comma
                                   (default *name,uuid,state,received,runtime,worker*)
  --unix-socket                    path to unix socket to bind flower server to
  --url-prefix                     base url prefix
  --xheaders                       enable support for the 'X-Real-Ip' and
                                   'X-Scheme' headers. (default *False*)

TORNADO OPTIONS
===============

  --log-file-max-size              max size of log files before rollover
                                   (default *100000000*)
  --log-file-num-backups           number of log files to keep (default *10*)
  --log-file-prefix=PATH           Path prefix for log files. Note that if you
                                   are running multiple tornado processes,
                                   log_file_prefix must be different for each
                                   of them (e.g. include the port number)
  --log-to-stderr                  Send log output to stderr (colorized if
                                   possible). By default use stderr if
                                   ``--log-file-prefix`` is not set and no other
                                   logging is configured.
  --logging=LEVEL                  Set the Python log level to *debug*, *info*,
                                   *warning*, *error* or *none*. If *none*,
                                   tornado won't touch the logging
                                   configuration. (default *info*)

USAGE
=====

Launch the Flower server at specified port other than default 5555 (open the UI at http://localhost:5566): ::

    $ celery flower --port=5566

Specify Celery application path with address and port for Flower: ::

    $ celery -A proj flower --address=127.0.0.6 --port=5566

Broker URL and other configuration options can be passed through the standard Celery options (notice that they are after
Celery command and before Flower sub-command): ::

    $ celery -A proj --broker=amqp://guest:guest@localhost:5672// flower
