#!/bin/bash -eu
exec flower '--broker=${CELERY_EXPORTER_BROKER_URL}'
