.. _authentication:
Authentication
==============

Protecting your Flower instance from unwarranted access is important
if it runs in an untrusted environment. Below, we outline the various
forms of authentication supported by Flower.

**NOTE:** The following endpoints are exempt from authentication:

- /healthcheck
- /metrics

.. _basic-auth:

HTTP Basic Authentication
-------------------------

Securing Flower with Basic Authentication is easy.

The `--basic_auth` option accepts `user:password` pairs separated by
a comma. If configured, any client trying to access this
Flower instance will be prompted to provide the credentials specified in
this argument: ::

    $ celery flower --basic_auth=user1:password1,user2:password2

See also :ref:`reverse-proxy`

.. _google-oauth:

Google OAuth 2.0
----------------

Flower supports Google OAuth 2.0. This way you can authenticate any user
with a Google account. Google OAuth 2.0 authentication is enabled using the
`--auth`, `--oauth2_key`, `--oauth2_secret` and `--oauth2_redirect_uri` options.

`--auth` is a regular expression, for granting access only to the specified email pattern.
`--oauth2_key` and `--oauth2_secret` are your credentials from your `Google Developer Console`_.
`--oauth2_redirect_uri` is there to specify what is the redirect_uri associated to your key and secret

For instance, if you want to grant access to `me@gmail.com` and `you@gmail.com`: ::

    $ celery flower --auth="me@gmail.com|you@gmail.com" --oauth2_key=... --oauth2_secret=... --oauth2_redirect_uri=http://flower.example.com/login

Alternatively, you can set environment variables instead of command line arguments: ::

    $ export FLOWER_OAUTH2_KEY=...
    $ export FLOWER_OAUTH2_SECRET=...
    $ export FLOWER_OAUTH2_REDIRECT_URI=http://flower.example.com/login
    $ celery flower --auth=.*@example\.com

.. _Google Developer Console: https://console.developers.google.com

.. _github-oauth:

Okta OAuth
------------

Flower also supports Okta OAuth. Flower should be registered in
<https://developer.okta.com/docs/guides/add-an-external-idp/openidconnect/register-app-in-okta/>
before getting started. See `Okta OAuth API`_ docs for more info.

Okta OAuth should be activated using `--auth_provider` option.
The client id, secret and redirect uri should be provided using
`--oauth2_key`, `--oauth2_secret`, `--oauth2_redirect_uri` options or using
`FLOWER_OAUTH2_KEY`, `FLOWER_OAUTH2_SECRET`, `FLOWER_OAUTH2_REDIRECT_URI` environment variables.

 The URL from which OAuth2 API URLs will be built should be set using `FLOWER_OAUTH2_OKTA_BASE_URL`
  environment variable: ::

    $ export FLOWER_OAUTH2_KEY=7956724aafbf5e1a93ac
    $ export FLOWER_OAUTH2_SECRET=f9155f764b7e466c445931a6e3cc7a42c4ce47be
    $ export FLOWER_OAUTH2_REDIRECT_URI=http://localhost:5555/login
    $ export FLOWER_OAUTH2_OKTA_BASE_URL=https://my-company.okta.com/oauth2
    $ celery flower --auth_provider=flower.views.auth.OktaLoginHandler --auth=.*@example\.com

.. _Okta OAuth API: https://developer.okta.com/docs/reference/api/oidc/

GitHub OAuth
------------

Flower also supports GitHub OAuth. Flower should be registered in
<https://github.com/settings/applications/new> before getting started.
See `GitHub OAuth API`_ docs for more info.

GitHub OAuth should be activated using `--auth_provider` option.
The client id, secret and redirect uri should be provided using
`--oauth2_key`, `--oauth2_secret` and `--oauth2_redirect_uri` options or using
`FLOWER_OAUTH2_KEY`, `FLOWER_OAUTH2_SECRET` and `FLOWER_OAUTH2_REDIRECT_URI`
environment variables. ::

    $ export FLOWER_OAUTH2_KEY=7956724aafbf5e1a93ac
    $ export FLOWER_OAUTH2_SECRET=f9155f764b7e466c445931a6e3cc7a42c4ce47be
    $ export FLOWER_OAUTH2_REDIRECT_URI=http://localhost:5555/login
    $ celery flower --auth_provider=flower.views.auth.GithubLoginHandler --auth=.*@example\.com

.. _GitHub OAuth API: https://developer.github.com/v3/oauth/

.. _gitlab-oauth:

GitLab OAuth
------------

Flower also supports GitLab OAuth. Flower should be registered in
<https://gitlab.com/profile/applications> before getting started.
See `GitLab OAuth2 API`_ docs for more info.

GitLab OAuth should be activated using `--auth_provider` option.
The client id, secret and redirect uri should be provided using
`--oauth2_key`, `--oauth2_secret` and `--oauth2_redirect_uri` options or using
`FLOWER_OAUTH2_KEY`, `FLOWER_OAUTH2_SECRET` and `FLOWER_OAUTH2_REDIRECT_URI`
environment variables.

A list of allowed GitLab groups can be specified using the
 `FLOWER_GITLAB_AUTH_ALLOWED_GROUPS` environment variable (e.g. ``group1,group2/subgroup``).

The default minimum required group access level can be changes by
`FLOWER_GITLAB_MIN_ACCESS_LEVEL` environment variable.
See `Group and project members API`_ for details.

    $ export FLOWER_OAUTH2_KEY=7956724aafbf5e1a93ac
    $ export FLOWER_OAUTH2_SECRET=f9155f764b7e466c445931a6e3cc7a42c4ce47be
    $ export FLOWER_OAUTH2_REDIRECT_URI=http://localhost:5555/login
    $ export FLOWER_GITLAB_AUTH_ALLOWED_GROUPS=group1,group2/subgroup
    $ celery flower --auth_provider=flower.views.auth.GitLabLoginHandler --auth=.*@example\.com

.. _GitLab OAuth2 API: https://docs.gitlab.com/ee/api/oauth2.html
.. _Group and project members API: https://docs.gitlab.com/ee/api/members.html
