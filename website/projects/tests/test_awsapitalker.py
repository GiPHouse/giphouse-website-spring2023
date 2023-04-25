import json

import boto3

from django.test import TestCase

from moto import mock_organizations

from projects import awsapitalker


class AWSAPITalkerTest(TestCase):
    """Test AWSAPITalker class."""

    def setUp(self):
        """Set up testing environment."""
        self.mock_org = mock_organizations()
        self.api_talker = awsapitalker.AWSAPITalker()
        self.mock_org.start()

    def tearDown(self):
        self.mock_org.stop()

    def test_create_organization(self):
        response = self.api_talker.create_organization("ALL")
        self.assertIsNotNone(response)
        self.assertEquals(response["Organization"]["FeatureSet"], "ALL")

    def test_create_organizational_unit(self):
        org_info = self.api_talker.create_organization("ALL")
        org_id = org_info["Organization"]["Id"]

        response = self.api_talker.create_organizational_unit(org_id, "Test OU")

        self.assertIsNotNone(response)
        self.assertEqual(response["OrganizationalUnit"]["Name"], "Test OU")

    def test_attach_policy(self):
        moto_client = boto3.client("organizations")

        org_info = self.api_talker.create_organization("ALL")
        org_id = org_info["Organization"]["Id"]

        policy_name = "test_policy"
        policy_document = {"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}
        policy_id = moto_client.create_policy(
            Name=policy_name,
            Content=json.dumps(policy_document),
            Type="SERVICE_CONTROL_POLICY",
            Description="Policy for testing purposes",
        )["Policy"]["PolicySummary"]["Id"]

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

        eval_results = self.api_talker.simulate_principal_policy(arn, ["iam:SimulatePrincipalPolicy"])["EvaluationResults"]

        self.assertEquals(eval_results[0]["EvalDecision"], "allowed")
    
    def test_describe_organization(self):

        self.api_talker.create_organization("ALL")
        response = self.api_talker.describe_organization()
        self.assertIsNotNone(response)
        self.assertIn("Organization", response)
        self.assertIn("MasterAccountId", response["Organization"])
        self.assertIn("MasterAccountEmail", response["Organization"])

    def test_describe_policy(self):
        moto_client = boto3.client("organizations")

        self.api_talker.create_organization("ALL")

        policy_content = json.dumps(
            {"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}
        )
        policy_id = moto_client.create_policy(
            Name="Test policy",
            Content=policy_content,
            Type="SERVICE_CONTROL_POLICY",
            Description="Policy for testing purposes",
        )["Policy"]["PolicySummary"]["Id"]

        policy = self.api_talker.describe_policy(policy_id)["Policy"]
        policy_summary = policy["PolicySummary"]

        self.assertEquals(policy_summary["Name"], "Test policy")
        self.assertEquals(policy_summary["Description"], "Policy for testing purposes")
        self.assertEquals(policy_content, policy["Content"])

    def test_create_account(self):
        moto_client = boto3.client("organizations")

        self.api_talker.create_organization("ALL")

        response = self.api_talker.create_account("test@example.com", "Test")

        accounts = moto_client.list_accounts()["Accounts"]

        self.assertIsNotNone(response)
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
