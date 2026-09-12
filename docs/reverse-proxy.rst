.. _reverse-proxy:

Running behind reverse proxy
============================

To run `Flower` behind a reverse proxy, remember to pass the correct `Host`
header to Flower so it can generate correct URLs.

The following block represents the minimal `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name flower.example.com;

        location / {
            proxy_pass http://localhost:5555;
        }
    }

If you run Flower under a custom location, make sure the :ref:`url_prefix` option
matches the location path.

Set either the `FLOWER_URL_PREFIX=flower` environment variable
or the `--url-prefix=flower` command line option. With that set,
use the following `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name example.com;

        location /flower/ {
            proxy_pass http://localhost:5555/flower/;
        }
    }

Without `url_prefix` the Flower frontend cannot generate
correct static links, and without the trailing `/flower/` in the `proxy_pass`
parameter the browser ends up at a 404 page.

Note that you should not expose this site to the public internet without
any sort of authentication. If you have an `htpasswd` file with user
credentials you can make `nginx` use this file by adding the following
lines to the location block:

.. code-block:: nginx

    auth_basic "Restricted";
    auth_basic_user_file htpasswd;
