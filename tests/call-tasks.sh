#!/bin/bash
set -e

N=${1:-10}

for i in $(seq 1 $N); do
    celery call -A tasks tasks.add --args="[$i,$i]";
done

celery call -A tasks tasks.sleep --args='[10]'
celery call -A tasks tasks.error --args='[10]'
