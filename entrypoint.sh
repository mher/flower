#!/bin/sh -eu
exec $(which flower) "--broker=${CELERY_EXPORTER_BROKER_URL}"
