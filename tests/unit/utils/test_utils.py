import unittest

from flower.utils import bugreport
from celery import Celery


class BugreportTests(unittest.TestCase):
    def test_default(self):
        report = bugreport()
        self.assertFalse('Unknown Celery version' in report)
        self.assertTrue('tornado' in report)
        self.assertTrue('babel' in report)
        self.assertTrue('celery' in report)

    def test_with_app(self):
        app = Celery()
        report = bugreport(app)
        self.assertFalse('Unknown Celery version' in report)
        self.assertTrue('tornado' in report)
        self.assertTrue('babel' in report)
        self.assertTrue('celery' in report)
