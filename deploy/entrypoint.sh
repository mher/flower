#!/bin/bash

ENV="${ENV:-""}"
HOSTNAME="${HOSTNAME:-""}"

if [ "$ENV" == "" ];
then
    echo "Environment variable 'ENV' cannot be empty"
    exit 1
fi

if [ "$HOSTNAME" == "" ];
then
    echo "Environment variable 'HOSTNAME' cannot be empty"
    exit 1
fi

cd /workspace/flower

export DD_LOGS_INJECTION=true
export DD_SERVICE=flower
export DD_ENV="$ENV"
python flower/__main__.py --broker=$HEYGEN_BROKER_URL flower --conf=flowerconfig.py