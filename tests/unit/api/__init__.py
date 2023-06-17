import os

from tests.unit import AsyncHTTPTestCase


class BaseApiTestCase(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        os.environ['FLOWER_UNAUTHENTICATED_API'] = 'true'

    def tearDown(self):
        super().tearDown()
        del os.environ['FLOWER_UNAUTHENTICATED_API']
