"""Tests for awssync.py."""

from django.test import TestCase

from courses.models import Semester

from projects import awssync
from projects.models import Project

from mailing_lists.models import MailingList


class AWSSyncTest(TestCase):
    """Test AWSSync class."""

    def setUp(self):
        """Set up testing environment."""
        self.sync = awssync.AWSSync()
        self.semester = Semester.objects.create(year=2023, season=Semester.SPRING)
        self.mailing_list = MailingList.objects.create(address="test1")
        self.project = Project.objects.create(id=1, name="test1", github_team_id=1, semester=self.semester)
        self.mailing_list.projects.add(self.project)

    def test_button_pressed(self):
        """Test button_pressed function."""
        return_value = self.sync.button_pressed()
        self.assertTrue(return_value)

    def test_get_all_mailing_lists(self):
        """Test get_all_mailing_lists function."""
        mailing_lists = self.sync.get_all_mailing_lists()
        self.assertIsInstance(mailing_lists, list)

    def test_get_emails_with_teamids(self):
        """Test get_emails_with_teamids function."""
        email_id = self.sync.get_emails_with_teamids()
        self.assertIsInstance(email_id, list)
        self.assertIsInstance(email_id[0], tuple)
        expected_result = [("test1@giphouse.nl", 11)]
        self.assertEqual(email_id, expected_result)
