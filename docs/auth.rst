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

Flower also supports GitLab OAuth for authentication. To enable GitLab OAuth, follow the steps below:

1. Register Flower as an application at GitLab. You can refer to the `GitLab OAuth documentation`_ for detailed instructions on how to do this.
2. Once registered, you will obtain the credentials for Flower configuration.
3. In your Flower configuration, set the following options to activate GitLab OAuth:
    - :ref:`auth_provider` to `flower.views.auth.GitLabLoginHandler`.
    - :ref:`oauth2_key` to the "Application ID" obtained from GitLab.
    - :ref:`oauth2_secret` to the "Secret" obtained from GitLab.
    - :ref:`oauth2_redirect_uri`: Set this to the redirect URI configured in GitLab.
4. (Optional) To restrict access to specific GitLab groups, you can utilize the `FLOWER_GITLAB_AUTH_ALLOWED_GROUPS` environment variable. Set it to a comma-separated list of allowed groups. You can include subgroups by using the `/` character. For example: `group1,group2/subgroup`.
5. (Optional) The default minimum required group access level can be adjusted using the `FLOWER_GITLAB_MIN_ACCESS_LEVEL` environment variable.
6. (Optional) The custom GitHub Domain can be adjusted using the `FLOWER_GITLAB_OAUTH_DOMAIN` environment variable.

For further details on GitLab OAuth and its implementation, refer to the `Group and project members API`_ documentation.
It provides comprehensive information and guidelines on working with GitLab's OAuth functionality.

See also `GitLab OAuth2 API`_ documentation for more info.

.. _GitLab OAuth documentation: https://docs.gitlab.com/ee/integration/oauth_provider.htm
.. _GitLab OAuth2 API: https://docs.gitlab.com/ee/api/oauth2.html
.. _Group and project members API: https://docs.gitlab.com/ee/api/members.html
