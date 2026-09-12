Prometheus Integration
======================

Flower exports several celery worker and task metrics in Prometheus' format.
The ``/metrics`` endpoint is available from the get go after you have installed Flower.

By default on your local machine Flower's metrics are available at: ``localhost:5555/metrics``.

Read further for more information about configuration and available metrics please.

Complete guide on integration of Celery, Flower, Prometheus and Grafana is here: `Grafana Integration Guide`_.

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

You can also just point Prometheus at the example ``prometheus.yml`` file in the root of the `Flower repository <https://github.com/mher/flower/blob/master/prometheus.yml>`_
when you start it from the command line (note that you would have to set ``flower`` to point at ``localhost`` in your ``etc/hosts`` config for the DNS to resolve correctly)::

    ./prometheus --config.file=prometheus.yml

Available Metrics
-----------------

Below you will find a table of available Prometheus metrics exposed by Flower.

+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| Name                                              | Description                                                          |  Labels            | Instrument Type |
+===================================================+======================================================================+====================+=================+
| flower_events_total                               | Number of times a celery task event was registered by Flower.        | task, type, worker | counter         |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_task_prefetch_time_seconds                 | The time the task spent waiting at the celery worker to be executed. | task, worker       | gauge           |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_worker_prefetched_tasks                    | Number of tasks of given type prefetched at a worker.                | task, worker       | gauge           |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_task_runtime_seconds                       | The time it took to run the task.                                    | task, worker       | histogram       |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_worker_online                              | Shows celery worker's online status.                                 | worker             | gauge           |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+
| flower_worker_number_of_currently_executing_tasks | Number of tasks currently executing at this worker.                  | worker             | gauge           |
+---------------------------------------------------+----------------------------------------------------------------------+--------------------+-----------------+

Using Metric Labels
-------------------

You can filter received data in prometheus using ``promql`` syntax to present information only for selected labels.
We have the following labels available:

* **task** - task name, i.e. ``tasks.add``, ``tasks.multiply``.
* **type** - task event type, i.e. ``task-started``, ``task-succeeded``. Note that worker related events **will not be counted**.
  For more info on task event types see: `task events in celery <https://docs.celeryq.dev/en/stable/userguide/monitoring.html#task-events>`_.
* **worker** - celery worker name, i.e ``celery@<your computer name>``.

Example Prometheus Alerts
-------------------------

See example `Prometheus alerts <https://github.com/mher/flower/tree/master/examples/prometheus-alerts.yaml>`_.
Add the rules to your ``alertmanager.yml`` config as in the `alert manager's documentation <https://prometheus.io/docs/alerting/latest/configuration/>`_.


Example Grafana Dashboard
-------------------------

See example `Grafana dashboard <https://github.com/mher/flower/tree/master/examples/celery-monitoring-grafana-dashboard.json>`_.
You can import it easily in Grafana.
Hover over the + button in the side bar menu -> Import -> Upload JSON file.
The dashboard should give you a nice starting point for monitoring of your celery cluster.

Grafana Integration Guide
=========================

The quickest way to see the whole stack working is the `docker-compose.yml`_ file in the root of
the Flower repository. It starts Redis, a Celery worker, Flower, Prometheus and Grafana.
Prometheus is configured to scrape Flower, and Grafana is provisioned with the Prometheus data
source and the Celery monitoring dashboard, so nothing has to be set up by hand.

.. _docker-compose.yml: https://github.com/mher/flower/blob/master/docker-compose.yml

Start the stack
---------------

From a checkout of the repository run::

    docker compose up --build

Once the containers are up, the services are available at:

- Flower at http://localhost:5555
- Prometheus at http://localhost:9090
- Grafana at http://localhost:3000

Submit a few tasks so there is something to look at::

    curl -X POST -d '{"args":[1,2]}' http://localhost:5555/api/task/async-apply/tasks.add

Check Prometheus
----------------

Open http://localhost:9090, go to the `Graph` tab and start typing `flower`. The autocomplete
lists all metrics exported by Flower.

.. image:: screenshots/flower-metrics-in-prometheus.png
   :width: 100%

Open the dashboard in Grafana
-----------------------------

Open http://localhost:3000. Anonymous access is enabled and the Celery monitoring dashboard is
the home page, so no login is needed.

.. image:: screenshots/grafana-dashboard.png
   :width: 100%

Import the dashboard into an existing Grafana
---------------------------------------------

If you already run Prometheus and Grafana, add Flower as a scrape target as described in
`Configure Prometheus to scrape Flower metrics`_ and add Prometheus as a data source in Grafana
following the `Grafana data source documentation`_. Then import the dashboard.

Download the `Grafana dashboard`_ JSON file.

Hover over the `+` icon in the left side-bar and click `Import`.

.. image:: screenshots/grafana-import-dashboard.png
   :width: 30%

Click `Upload JSON file` and select the `celery-monitoring-grafana-dashboard.json` file.

.. image:: screenshots/grafana-import-celery-monitoring-dashboard.png
   :width: 100%

Select your Prometheus data source in the `Prometheus` field and click `Import`.

.. image:: screenshots/grafana-configure-imported-dashboard.png
   :width: 100%

.. _Grafana dashboard: https://github.com/mher/flower/blob/master/examples/celery-monitoring-grafana-dashboard.json
.. _Grafana data source documentation: https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/
