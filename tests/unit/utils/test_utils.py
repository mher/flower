import unittest
from unittest.mock import Mock

from flower.utils import bugreport
from celery import Celery


class BugreportTests(unittest.TestCase):
    def test_default(self):
        report = bugreport()
        self.assertFalse('Error when generating bug report' in report)
        self.assertTrue('tornado' in report)
        self.assertTrue('humanize' in report)
        self.assertTrue('celery' in report)

    def test_with_app(self):
        app = Celery()
        report = bugreport(app)
        self.assertFalse('Error when generating bug report' in report)
        self.assertTrue('tornado' in report)
        self.assertTrue('humanize' in report)
        self.assertTrue('celery' in report)

    def test_when_unable_to_generate_report(self):
        fake_app = Mock()
        fake_app.bugreport.side_effect = ImportError('import error message')
        report = bugreport(fake_app)
        self.assertTrue('Error when generating bug report' in report)
        self.assertTrue('import error message' in report)
        self.assertTrue("Have you installed correct versions of Flower's dependencies?" in report)
