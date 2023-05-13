#!/bin/bash
set -e

export ROOT_DIR=$(git rev-parse --show-toplevel)
export PYTHONPATH="$PYTHONPATH:$ROOT_DIR/examples"

N=${1:-10}

for i in $(seq 1 $N); do
    celery -A tasks call tasks.add --args="[$i,$i]";
done

celery -A tasks call tasks.sleep --args='[100]'
celery -A tasks call tasks.error --args='[10]'
