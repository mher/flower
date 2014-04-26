.. _reverse-proxy:

Running behind reverse proxy
============================

To run `Flower` behind a reverse proxy, remember to set the correct `Host` 
header to the request to make sure Flower can generate correct URLs.
The following is a minimal `nginx` configuration:

.. code-block:: nginx

    server {
        listen 80;
        server_name flower.example.com;
        charset utf-8;

        location / {
            proxy_pass http://localhost:5555;
            proxy_set_header Host $host;
            proxy_redirect off;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }

Note that you should not expose this site to the public internet without
any sort of authentication! If you have a `htpasswd` file with user
credentials you can make `nginx` use this file by adding the following
lines to the location block:

.. code-block:: nginx

    auth_basic "Restricted";
    auth_basic_user_file htpasswd;
