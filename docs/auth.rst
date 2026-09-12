.. _authentication:

Authentication
==============

Flower supports a variety of authentication methods, including Basic Authentication, Google, GitHub,
GitLab, and Okta OAuth. You can also customize and use your own authentication method.

The following endpoints are exempt from authentication:

- /healthcheck
- /metrics

.. _basic-authentication:

HTTP Basic Authentication
-------------------------

Flower supports Basic Authentication as a built-in authentication method, allowing you to secure access to the
Flower using simple username and password credentials. This authentication method is commonly used for
straightforward authentication requirements.

To enable basic authentication, use :ref:`basic_auth` option. This option allows you to specify a list of
username and password pairs for authentication.

For example, running Flower with the following :ref:`basic_auth` option will protect the Flower UI and
only allow access to users providing the username user and the password pswd::

    $ celery flower --basic-auth=user:pswd

By default ``/metrics`` is unauthenticated. To require basic auth for ``/metrics``, add this to your
config file:

.. code-block:: python

    # flowerconfig.py
    import tornado.web
    from flower.views.monitor import Metrics

    Metrics.get = tornado.web.authenticated(Metrics.get)

and run Flower with the :ref:`conf` option::

    $ celery flower --basic-auth=user:pswd --conf=flowerconfig.py

To disable ``/metrics`` entirely:

.. code-block:: python

    # flowerconfig.py
    import tornado.web
    from flower.views.monitor import Metrics

    async def disabled(self):
        raise tornado.web.HTTPError(404)

    Metrics.get = disabled

See also :ref:`reverse-proxy`

.. _google-oauth:

Google OAuth
------------

Flower provides authentication support using Google OAuth, enabling you to authenticate users through their Google accounts.
This integration simplifies the authentication process and offers a seamless experience for users who are already logged into Google.

Follow the steps below to configure and use Google OAuth authentication:

1. Go to the `Google Developer Console`_
2. Select a project, or create a new one.
3. In the sidebar on the left, select Credentials.
4. Click CREATE CREDENTIALS and click OAuth client ID.
5. Under Application type, select Web application.
6. Name OAuth 2.0 client and click Create.
7. Copy the "Client secret" and "Client ID"
8. Add redirect URI to the list of Authorized redirect URIs

Here's an example configuration file with the Google OAuth options:

.. code-block:: python

    auth_provider="flower.views.auth.GoogleAuth2LoginHandler"
    auth="allowed-emails.*@gmail.com"
    oauth2_key="<your_client_id>"
    oauth2_secret="<your_client_secret>"
    oauth2_redirect_uri="http://localhost:5555/login"

Replace `<your_client_id>` and `<your_client_secret>` with the actual  Client ID and secret obtained from
the Google Developer Console.

.. _Google Developer Console: https://console.developers.google.com

.. _github-oauth:

GitHub OAuth
------------

Flower also supports GitHub OAuth. Before getting started, Flower should be registered in
`Github Settings`_.

Github OAuth is activated by setting :ref:`auth_provider` to `flower.views.auth.GithubLoginHandler`.
Here's an example configuration file with the Github OAuth options:

.. code-block:: python

    auth_provider="flower.views.auth.GithubLoginHandler"
    auth="allowed-emails.*@gmail.com"
    oauth2_key="<your_client_id>"
    oauth2_secret="<your_client_secret>"
    oauth2_redirect_uri="http://localhost:5555/login"

Replace `<your_client_id>` and `<your_client_secret>` with the actual  Client ID and secret obtained from
the Github Settings.

See `GitHub OAuth API`_ docs for more info.

.. _Github Settings: https://github.com/settings/applications/new
.. _GitHub OAuth API: https://developer.github.com/v3/oauth/

.. _okta-oauth:

Okta OAuth
----------

Flower also supports Okta OAuth. Before getting started, you need to register Flower in `Okta`_.
Okta OAuth is activated by setting :ref:`auth_provider` option to `flower.views.auth.OktaLoginHandler`.

Okta OAuth requires `oauth2_key`, `oauth2_secret` and `oauth2_redirect_uri` options which should be obtained from Okta.
Okta OAuth also uses `FLOWER_OAUTH2_OKTA_BASE_URL` environment variable.

See Okta `Okta OAuth API`_ docs for more info.

.. _Okta: https://developer.okta.com/docs/guides/add-an-external-idp/openidconnect/main/
.. _Okta OAuth API: https://developer.okta.com/docs/reference/api/oidc/

.. _gitlab-oauth:

GitLab OAuth
------------

Flower also supports GitLab OAuth. Before getting started, Flower should be registered as an
application in GitLab, see the `GitLab OAuth documentation`_ for the steps.

GitLab OAuth is activated by setting :ref:`auth_provider` to `flower.views.auth.GitLabLoginHandler`.
Here's an example configuration file with the GitLab OAuth options:

.. code-block:: python

    auth_provider="flower.views.auth.GitLabLoginHandler"
    auth=".*@example.com"
    oauth2_key="<your_application_id>"
    oauth2_secret="<your_secret>"
    oauth2_redirect_uri="http://localhost:5555/login"

Replace `<your_application_id>` and `<your_secret>` with the "Application ID" and "Secret" obtained
from GitLab, and set `oauth2_redirect_uri` to the redirect URI configured there.
The :ref:`auth` option is matched against the email address of the GitLab user.

The following environment variables are optional:

- `FLOWER_GITLAB_AUTH_ALLOWED_GROUPS` restricts access to members of the listed groups.
  Set it to a comma-separated list of group paths. Subgroups are written with a `/`,
  for example `group1,group2/subgroup`. By default, any group membership is accepted.
- `FLOWER_GITLAB_MIN_ACCESS_LEVEL` sets the minimum `access level`_ a user must have in one of
  the allowed groups. The default is `20` (Reporter). It only applies when
  `FLOWER_GITLAB_AUTH_ALLOWED_GROUPS` is set.
- `FLOWER_GITLAB_OAUTH_DOMAIN` sets the domain of a self-managed GitLab instance.
  The default is `gitlab.com`.

See `GitLab OAuth2 API`_ and `Group members API`_ documentation for more info.

.. _GitLab OAuth documentation: https://docs.gitlab.com/integration/oauth_provider/
.. _GitLab OAuth2 API: https://docs.gitlab.com/api/oauth2/
.. _Group members API: https://docs.gitlab.com/api/group_members/
.. _access level: https://docs.gitlab.com/api/access_requests/#valid-access-levels

Logging out
-----------

When OAuth is enabled, the navigation bar shows a logout link that ends the Flower session.
The OAuth provider keeps its own session, so logging in again may not ask for credentials.

.. _custom-authentication:

Custom authentication providers
-------------------------------

Custom providers let Flower integrate with authentication services that are
not supported by the built-in handlers.

A custom handler can subclass a built-in handler to modify its behavior, or
inherit from ``flower.views.BaseHandler`` to implement a new authentication
flow.

The :ref:`auth_provider` option accepts the fully qualified import path of a
custom login handler. For example::

    myproject/
        __init__.py
        auth.py
        celery_app.py
        provider.py

Flower uses the handler for its ``/login`` route. The handler must authenticate
the request, set the secure ``user`` cookie to an identity accepted by
:ref:`auth`, and redirect the user after a successful login. It is also
responsible for validating provider responses and rejecting failed logins.

For example, a handler can delegate authentication to an application function
that returns a verified identity, or ``None`` when authentication fails:

.. code-block:: python

    from tornado import web

    from flower.views import BaseHandler
    from myproject.provider import authenticate


    class CustomLoginHandler(BaseHandler):
        async def get(self):
            identity = await authenticate(self.request)
            if not identity:
                raise web.HTTPError(403, "Authentication failed")

            self.set_secure_cookie("user", identity)
            self.redirect(self.get_argument("next", "/"))

Start Flower with::

    $ celery -A myproject.celery_app flower \
        --auth-provider=myproject.auth.CustomLoginHandler \
        --auth='.*@example.com'

The module must be importable from Flower's Python environment.
