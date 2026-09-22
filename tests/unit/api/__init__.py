import os
from unittest.mock import patch

from tests.unit import AsyncHTTPTestCase


class BaseApiTestCase(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ, {'FLOWER_UNAUTHENTICATED_API': 'true'})
        self.addCleanup(environment.stop)
        environment.start()
