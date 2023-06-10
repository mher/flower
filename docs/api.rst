API Reference
=============

For security reasons, the Flower API is disabled by default when authentication is not enabled.
To enable the API for unauthenticated environments, you can set the FLOWER_UNAUTHENTICATED_API
environment variable to true.

.. autotornado:: flower.app:Flower()
