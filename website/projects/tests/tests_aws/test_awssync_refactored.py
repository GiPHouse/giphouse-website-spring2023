"""Tests for awssync_refactored.py."""
from django.test import TestCase

from projects.aws.awssync_refactored import AWSSyncRefactored


class AWSSyncRefactoredTest(TestCase):
    def setUp(self):
        self.sync = AWSSyncRefactored()
