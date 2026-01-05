.. _reverse-proxy:

Running behind reverse proxy
============================

To run `Flower` behind a reverse proxy, remember to set the correct `Host`
header to the request to make sure Flower can generate correct URLs.

The following block represents the minimal `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name flower.example.com;

        location / {
            proxy_pass http://localhost:5555;
        }
    }

If you run Flower behind custom location, make sure :ref:`url_prefix` option
value equals to the location path.

You have to use either environment variable `FLOWER_URL_PREFIX=flower`
or command parameter `--url_prefix=flower` when you run it
via `celery`. With that being set you need the following `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name example.com;

        location /flower/ {
            proxy_pass http://localhost:5555/flower/;
        }
    }

without `url_prefix` Flower frontend won't be able to generate
correct static links, and without `/flower/` at the end of `proxy_pass`
parameter, the browser will lead you to 404.

Note that you should not expose this site to the public internet without
any sort of authentication! If you have a `htpasswd` file with user
credentials you can make `nginx` use this file by adding the following
lines to the location block:

.. code-block:: nginx

    auth_basic "Restricted";
    auth_basic_user_file htpasswd;
