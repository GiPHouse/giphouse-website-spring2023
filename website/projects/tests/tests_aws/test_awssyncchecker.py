import logging
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from django.test import TestCase

from moto import mock_iam, mock_organizations, mock_sts

from projects.aws.awssyncchecker import AWSSyncChecker
from projects.aws.awssyncchecker_permissions import api_permissions


@mock_sts
@mock_organizations
@mock_iam
class AWSSyncCheckerTest(TestCase):
    def setUp(self):
        logger = logging.getLogger("AWSSyncCheckerTest")
        self.checker = AWSSyncChecker(logger)

    def mock_simulate_principal_policy(self, allow: bool, api_operations: list[str]):
        return MagicMock(
            return_value={
                "EvaluationResults": [
                    {"EvalActionName": api_operation_name, "EvalDecision": "allowed" if allow else "implicitDeny"}
                    for api_operation_name in api_operations
                ]
            }
        )

    def test_check_aws_api_connection(self):
        self.checker.check_aws_api_connection()

    def test_check_iam_policy(self):
        self.checker.api_talker.iam_client.simulate_principal_policy = self.mock_simulate_principal_policy(
            True, api_permissions
        )
        self.checker.check_iam_policy(api_permissions)

    def test_check_iam_policy__exception(self):
        self.checker.api_talker.iam_client.simulate_principal_policy = self.mock_simulate_principal_policy(
            False, api_permissions
        )
        self.assertRaises(Exception, self.checker.check_iam_policy, api_permissions)

    def test_check_organization_existence(self):
        self.checker.api_talker.create_organization("ALL")
        self.checker.check_organization_existence()

    def test_check_organization_existence__exception(self):
        self.assertRaises(ClientError, self.checker.check_organization_existence)

    def test_check_is_management_account(self):
        self.checker.api_talker.create_organization("ALL")
        self.checker.check_is_management_account()

    def test_check_is_management_account__exception(self):
        self.checker.api_talker.create_organization("ALL")

        mock_identity = self.checker.api_talker.sts_client.get_caller_identity()
        mock_identity["Account"] = "alice123"
        self.checker.api_talker.sts_client.get_caller_identity = MagicMock(return_value=mock_identity)

        self.assertRaises(Exception, self.checker.check_is_management_account)

    def test_check_scp_enabled(self):
        self.checker.api_talker.create_organization("ALL")

        self.checker.api_talker.org_client.enable_policy_type(
            RootId=self.checker.api_talker.org_client.list_roots()["Roots"][0]["Id"],
            PolicyType="SERVICE_CONTROL_POLICY",
        )

        self.checker.check_scp_enabled()

    def test_check_scp_enabled__exception(self):
        self.checker.api_talker.create_organization("ALL")

        args = {
            "RootId": self.checker.api_talker.org_client.list_roots()["Roots"][0]["Id"],
            "PolicyType": "SERVICE_CONTROL_POLICY",
        }

        _ = self.checker.api_talker.org_client.enable_policy_type(**args)
        response = self.checker.api_talker.org_client.disable_policy_type(**args)

        mock_describe_organization = self.checker.api_talker.describe_organization()
        mock_describe_organization["Organization"]["AvailablePolicyTypes"] = response["Root"]["PolicyTypes"]
        self.checker.api_talker.org_client.describe_organization = MagicMock(return_value=mock_describe_organization)

        self.assertRaises(Exception, self.checker.check_scp_enabled)

    def test_pipeline_preconditions(self):
        self.checker.api_talker.create_organization("ALL")

        self.checker.api_talker.iam_client.simulate_principal_policy = self.mock_simulate_principal_policy(
            True, api_permissions
        )

        self.checker.pipeline_preconditions(api_permissions)
