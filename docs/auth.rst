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

Google OAuth 2.0
----------------

Flower also supports Google OAuth 2.0. This way you can authenticate any user
with a Google account. Google OAuth 2.0 authentication is enabled using the
--auth, --oauth2_key, --oauth2_secret and --oauth2_redirect_uri options.

--auth is a regular expression, for granting access only to the specified email pattern.
--oauth2_key and --oauth2_secret are your credentials from your (Google Developer Console)[https://console.developers.google.com].
--oauth2_redirect_uri is there to specify what is the redirect_uri associated to you key and secret

For instance, if you want to grant access to `me@gmail.com` and `you@gmail.com`: ::

    $ celery flower --auth="me@gmail.com|you@gmail.com" --oauth2_key=... --oauth2_secret=... --auth2_redirect_uri=http://flower.example.com/login

Alternatively you can set environment variables instead of command line arguments: ::
 
    $ export GOOGLE_OAUTH2_KEY=...
    $ export GOOGLE_OAUTH2_SECRET=...
    $ export GOOGLE_OAUTH2_REDIRECT_URI=http://flower.example.com/login
    $ celery flower --auth=.*@example\.com
