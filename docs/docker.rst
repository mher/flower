Docker Usage
============

To run Flower via Docker, you'll need a broker running.  If you don't
have one, you can fire up a simple Redis instance with Docker from the
official Redis image.

    $ docker run --name localredis -p 6379:6379 --rm -d redis

Now, clone this repository (https://github.com/mher/flower), build flower from the Dockerfile, start the
container and open http://localhost:49555 ::

    $ docker build -t "flower" .
    $ docker run -d -p=49555:5555 --rm --name flower -e CELERY_BROKER_URL=redis://0.0.0.0:6379/0 flower flower --port=5555

For more information about running with Docker see
https://docs.docker.com/

