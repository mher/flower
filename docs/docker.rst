Docker Usage
============

Clone this repository, build flower from the Dockerfile, start the
container and open http://localhost:49555 ::

    $ docker build -t "flower" .
    $ docker run -d -p=49555:5555 flower flower --port=5555

For more information about running with Docker see
http://docs.docker.io/en/latest/
