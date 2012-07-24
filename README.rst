Celery Flower
=============

Web based Celery administration and monitoring tool. Screenshots_.

.. _Screenshots: https://github.com/mher/flower/tree/master/docs/screenshots

Features
--------

* Workers monitoring and management
* Configuration viewer
* Worker pool control
* Broker options viewer
* Queues management
* Tasks execution statistics
* Task viewer

Usage
-----

Launch the server and open http://localhost:8008: ::

    $ flower --port=8008

Or launch from celery: ::

    $ celery flower --port=8008

Installation
------------

To install, simply: ::

    $ pip install flower

