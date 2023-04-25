import json
from unittest.mock import MagicMock, patch

import boto3

from django.test import TestCase

from moto import mock_iam, mock_organizations, mock_sts

from projects.aws import awsapitalker


class AWSAPITalkerTest(TestCase):
    """Test AWSAPITalker class."""

    def setUp(self):
        """Set up testing environment."""
        self.mock_iam = mock_iam()
        self.mock_org = mock_organizations()
        self.mock_sts = mock_sts()
        # self.mock_iam.start()
        self.mock_org.start()
        self.mock_sts.start()
        self.api_talker = awsapitalker.AWSAPITalker()

    def tearDown(self):
        # self.mock_iam.stop()
        self.mock_org.stop()
        self.mock_sts.stop()

    def test_create_organization(self):
        response = self.api_talker.create_organization("ALL")

        self.assertEquals(response["Organization"]["FeatureSet"], "ALL")

    def test_create_organizational_unit(self):
        org_info = self.api_talker.create_organization("ALL")
        org_id = org_info["Organization"]["Id"]

        response = self.api_talker.create_organizational_unit(org_id, "Test OU")

        self.assertEqual(response["OrganizationalUnit"]["Name"], "Test OU")

    def test_attach_policy(self):
        moto_client = boto3.client("organizations")

        org_info = self.api_talker.create_organization("ALL")
        org_id = org_info["Organization"]["Id"]

        policy_id = self.create_dummy_policy()

        ou_info = self.api_talker.create_organizational_unit(org_id, "Test OU")
        ou_id = ou_info["OrganizationalUnit"]["Id"]

        self.api_talker.attach_policy(ou_id, policy_id)

        response = moto_client.list_policies_for_target(TargetId=ou_id, Filter="SERVICE_CONTROL_POLICY")
        self.assertIn(policy_id, [p["Id"] for p in response["Policies"]])

    def test_get_caller_identity(self):
        response = self.api_talker.get_caller_identity()
        self.assertIsNotNone(response)

    def test_simulate_principal_policy(self):
        arn = self.api_talker.get_caller_identity()["Arn"]

        with patch.object(
            self.api_talker.iam_client,
            "simulate_principal_policy",
            MagicMock(return_value={"EvaluationResults": [{"EvalDecision": "allowed"}]}),
        ):
            eval_results = self.api_talker.simulate_principal_policy(arn, ["sts:SimulatePrincipalPolicy"])[
                "EvaluationResults"
            ]

        self.assertEquals(eval_results[0]["EvalDecision"], "allowed")

    def test_describe_organization(self):
        self.api_talker.create_organization("ALL")

        response = self.api_talker.describe_organization()

        self.assertIn("Organization", response)
        self.assertIn("MasterAccountId", response["Organization"])
        self.assertIn("MasterAccountEmail", response["Organization"])

    def test_describe_policy(self):
        self.api_talker.create_organization("ALL")

        policy_id = self.create_dummy_policy()

        policy = self.api_talker.describe_policy(policy_id)["Policy"]
        policy_summary = policy["PolicySummary"]
        policy_content = self.create_dummy_policy_content()

        self.assertEquals(policy_summary["Name"], "Test policy")
        self.assertEquals(policy_summary["Description"], "Policy for testing purposes")
        self.assertEquals(policy_content, policy["Content"])

    def test_create_account(self):
        moto_client = boto3.client("organizations")

        self.api_talker.create_organization("ALL")

        response = self.api_talker.create_account("test@example.com", "Test")

        accounts = moto_client.list_accounts()["Accounts"]

        self.assertEquals(response["CreateAccountStatus"]["AccountName"], "Test")
        self.assertIn(("Test", "test@example.com"), [(account["Name"], account["Email"]) for account in accounts])

    def test_move_account(self):
        moto_client = boto3.client("organizations")

        org_info = self.api_talker.create_organization("ALL")
        org_id = org_info["Organization"]["Id"]

        account_status = self.api_talker.create_account("test@example.com", "Test")
        account_id = account_status["CreateAccountStatus"]["AccountId"]

        source_ou_info = self.api_talker.create_organizational_unit(org_id, "Source OU")
        source_ou_id = source_ou_info["OrganizationalUnit"]["Id"]
        dest_ou_info = self.api_talker.create_organizational_unit(org_id, "Destination OU")
        dest_ou_id = dest_ou_info["OrganizationalUnit"]["Id"]

        self.api_talker.move_account(account_id, source_ou_id, dest_ou_id)

        accounts_under_source = moto_client.list_children(ParentId=source_ou_id, ChildType="ACCOUNT")["Children"]
        accounts_under_dest = moto_client.list_children(ParentId=dest_ou_id, ChildType="ACCOUNT")["Children"]
        self.assertNotIn(account_id, [account["Id"] for account in accounts_under_source])
        self.assertIn(account_id, [account["Id"] for account in accounts_under_dest])

    def create_dummy_policy_content(self):
        """Returns a string containing the content of a policy used for testing."""
        return json.dumps({"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]})

    def create_dummy_policy(self):
        """
        Creates a policy used for testing.

        :return: ID of the created policy.
        """
        moto_client = boto3.client("organizations")

        policy_content = self.create_dummy_policy_content()

        return moto_client.create_policy(
            Name="Test policy",
            Content=policy_content,
            Type="SERVICE_CONTROL_POLICY",
            Description="Policy for testing purposes",
        )["Policy"]["PolicySummary"]["Id"]
