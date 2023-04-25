import logging

from django.test import TestCase

from projects.aws.awssyncchecker import AWSSyncChecker


class AWSSyncCheckerTest(TestCase):
    def setUp(self):
        logger = logging.getLogger("AWSSyncCheckerTest")
        self.checker = AWSSyncChecker(logger)

    def test_check_aws_api_connection(self):
        pass

    def test_check_iam_policy(self):
        pass

    def test_check_organization_existence(self):
        pass

    def test_check_is_management_account(self):
        pass

    def test_check_scp_enabled(self):
        pass

    def test_pipeline_preconditions(self):
        pass
