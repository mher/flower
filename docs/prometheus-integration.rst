Prometheus Integration
======================

Flower exports several celery worker and task metrics in Prometheus' format.
The ``/metrics`` endpoint is available from the get go after you have installed Flower.

By default on your local machine Flower's metrics are available at: ``localhost:5555/metrics``.

Read further for more information about configuration and available metrics please.

Configure Prometheus to scrape Flower metrics
---------------------------------------------

To integrate with Prometheus you have to add Flower as the target in Prometheus's configuration.
In this example we are assuming your Flower and Prometheus are installed on your local machine
with their defaults and available at ``localhost:<port number>``.

To add Flower's metrics to Prometheus go to its config file ``prometheus.yml`` which initially
will look like this:

.. code-block:: yaml

    global:
      scrape_interval:     15s
      evaluation_interval: 15s

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets: ['localhost:9090']

and alter the ``scrape_configs`` definition to be:

.. code-block:: yaml

    scrape_configs:
      - job_name: prometheus
        static_configs:
          - targets: ['localhost:9090']
      - job_name: flower
        static_configs:
          - targets: ['localhost:5555']

You can also just point Prometheus at the example ``prometheus.yml`` file in the root of the `Flower repository <https://github.com/mher/flower>`
when you start it from the command line (note that you would have to set ``flower`` to point at ``localhost`` in your ``etc/hosts`` config for the DNS to resolve correctly)::

    ./prometheus --config.file=prometheus.yml

Available Metrics
-----------------

Below you will find a table of available Prometheus metrics exposed by Flower.

+----------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| Name                             | Description                                                          |  Labels            | Instrument Type |
+==================================+======================================================================+====================+=================+
| flower_events_total              | Number of times a celery task event was registered by Flower.        | task, type, worker | counter         |
+----------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_task_queuing_time_seconds | The time the task spent waiting at the celery worker to be executed. | task, worker       | gauge           |
+----------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_task_runtime_seconds      | The time it took to run the task.                                    | task, worker       | histogram       |
+----------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_worker_online             | Shows celery worker's online status.                                 | worker             | gauge           |
+----------------------------------+----------------------------------------------------------------------+--------------------+-----------------+

Using Metric Labels
-------------------

You can filter received data in prometheus using ``promql`` syntax to present information only for selected labels.
We have the following labels available:

* **task** - task name, i.e. ``tasks.add``, ``tasks.multiply``.
* **type** - task event type, i.e. ``task-started``, ``task-succeeded``. Note that worker related events **will not be counted**.
  For more info on task event types see: `task events in celery <https://docs.celeryproject.org/en/stable/userguide/monitoring.html#task-events>`_.
* **worker** - celery worker name, i.e ``celery@<your computer name>``.

Example Prometheus Alerts
-------------------------

See example `Prometheus alerts <https://github.com/mher/flower/tree/master/examples/prometheus-alerts.yaml>`_.


Example Grafana Dashboard
-------------------------

See example `Grafana dashboard <https://github.com/mher/flower/tree/master/examples/celery-monitoring-grafana-dashboard.json>`_.
