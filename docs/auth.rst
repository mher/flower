Authentication
==============

Protecting your Flower instance from unwarranted access is important
if it runs in an untrusted environment. Below, we outline the various
forms of authentication supported by Flower.

.. _basic-auth:

HTTP Basic Authentication
-------------------------

Securing Flower with Basic Authentication is easy.

The `--basic_auth` option accepts `user:password` pairs separated by
semicolons. If configured, any client trying to access this
Flower instance will be prompted to provide the credentials specified in
this argument: ::

    $ celery flower --basic_auth=user1:password1,user2:password2

See also :ref:`reverse-proxy`

.. _google-openid:

Google OpenID
-------------

Flower also supports Google OpenID. This way you can authenticate any user
with a Google account. Google OpenID authentication is enabled using the
--auth option, which accepts a group of emails in the form of a regular
expression.

Grant access to Google accounts with email `me@gmail.com` and
`you@gmail.com`: ::

    $ celery flower --auth="me@gmail.com|you@gmail.com"

Grant access to all Google accounts having a domain of `example.com`: ::
 
    $ celery flower --auth=.*@example\.com
