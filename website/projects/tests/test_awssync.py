from unittest.mock import patch

import boto3

import botocore
from botocore.exceptions import ClientError

from django.test import TestCase

from moto import mock_organizations

from projects import awssync


class AWSSyncTest(TestCase):
    """Test AWSSync class."""

    def setUp(self):
        self.mock_org = mock_organizations()
        self.mock_org.start()
        self.sync = awssync.AWSSync()

    def tearDown(self):
        self.mock_org.stop()

    def test_button_pressed(self):
        return_value = self.sync.button_pressed()
        self.assertTrue(return_value)

    def test_create_aws_organization(self):
        moto_client = boto3.client("organizations")
        org = self.sync
        org.create_aws_organization()
        describe_org = moto_client.describe_organization()["Organization"]
        self.assertEqual(describe_org, org.org_info)

    def test_create_aws_organization__exception(self):
        org = self.sync
        with patch("botocore.client.BaseClient._make_api_call", AWSAPITalkerTest.mock_api):
            org.create_aws_organization()
        self.assertTrue(org.fail)
        self.assertIsNone(org.org_info)

    def test_create_course_iteration_OU(self):
        moto_client = boto3.client("organizations")
        org = self.sync
        org.create_aws_organization()
        org.create_course_iteration_OU(1)
        describe_unit = moto_client.describe_organizational_unit(OrganizationalUnitId=org.iterationOU_info["Id"])[
            "OrganizationalUnit"
        ]
        self.assertEqual(describe_unit, org.iterationOU_info)

    def test_create_iteration_OU_without_organization(self):
        org = self.sync
        org.create_course_iteration_OU(1)
        self.assertTrue(org.fail)

    def test_create_course_iteration_OU__exception(self):
        org = self.sync
        org.create_aws_organization()
        with patch("botocore.client.BaseClient._make_api_call", AWSAPITalkerTest.mock_api):
            org.create_course_iteration_OU(1)
        self.assertTrue(org.fail)

    def test_create_team_OU(self):
        moto_client = boto3.client("organizations")
        org = self.sync
        org.create_aws_organization()
        org.create_course_iteration_OU(1)
        org.create_team_OU("team1")
        describe_unit = moto_client.describe_organizational_unit(OrganizationalUnitId=org.iterationOU_info["Id"])[
            "OrganizationalUnit"
        ]
        self.assertEqual(describe_unit, org.iterationOU_info)

    def test_create_team_OU_without_iteration_OU(self):
        org = self.sync
        org.create_aws_organization()
        org.create_team_OU("team1")
        self.assertTrue(org.fail)

    def test_create_team_OU__exception(self):
        org = self.sync
        org.create_aws_organization()
        org.create_course_iteration_OU(1)
        with patch("botocore.client.BaseClient._make_api_call", AWSAPITalkerTest.mock_api):
            org.create_team_OU("team1")
        self.assertTrue(org.fail)


class AWSAPITalkerTest(TestCase):
    def mock_api(self, operation_name, kwarg):
        if operation_name == "CreateOrganization":
            raise ClientError(
                {
                    "Error": {
                        "Message": "The AWS account is already a member of an organization.",
                        "Code": "AlreadyInOrganizationException",
                    },
                    "ResponseMetadata": {
                        "RequestId": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                        "HTTPStatusCode": 400,
                        "HTTPHeaders": {
                            "x-amzn-requestid": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                            "content-type": "application/x-amz-json-1.1",
                            "content-length": "111",
                            "date": "Sun, 01 Jan 2023 00:00:00 GMT",
                            "connection": "close",
                        },
                        "RetryAttempts": 0,
                    },
                    "Message": "The AWS account is already a member of an organization.",
                },
                "create_organization",
            )
        if operation_name == "CreateOrganizationalUnit":
            raise ClientError(
                {
                    "Error": {
                        "Message": "The OU already exists.",
                        "Code": "ParentNotFoundException",
                    },
                    "ResponseMetadata": {
                        "RequestId": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                        "HTTPStatusCode": 400,
                        "HTTPHeaders": {
                            "x-amzn-requestid": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                            "content-type": "application/x-amz-json-1.1",
                            "content-length": "111",
                            "date": "Sun, 01 Jan 2023 00:00:00 GMT",
                            "connection": "close",
                        },
                        "RetryAttempts": 0,
                    },
                    "Message": "The OU already exists.",
                },
                "create_organizational_unit",
            )
        return botocore.client.BaseClient._make_api_call(self, operation_name, kwarg)
