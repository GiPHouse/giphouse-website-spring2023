from __future__ import annotations

import boto3

import logging

from projects.aws.awssyncchecker_permissions import api_permissions


class AWSSyncChecker:
    def __init__(self, logger: logging.Logger):
        self.required_aws_actions = api_permissions
        self.logger = logger

        # TODO: Replace with AWS API talker class object (pending sprint task).
        self.client_org = boto3.client("organizations")
        self.client_iam = boto3.client("iam")
        self.client_sts = boto3.client("sts")

    def check_aws_api_connection(self) -> None:
        """Check AWS API connection establishment with current boto3 credentials."""
        self.client_org.get_caller_identity()

    def check_iam_policy(self, desired_actions: list[str]) -> None:
        """Check permissions for list of AWS API actions."""
        iam_user_arn = self.client_sts.get_caller_identity()["Arn"]
        policy_evaluations = self.client_iam.simulate_principal_policy(
            PolicySourceArn=iam_user_arn, ActionNames=desired_actions
        )

        denied_api_actions = [
            evaluation_result["EvalActionName"]
            for evaluation_result in policy_evaluations["EvaluationResults"]
            if evaluation_result["EvalDecision"] != "allowed"
        ]

        if denied_api_actions:
            raise Exception(f"Some AWS API actions have been denied: {denied_api_actions}.")

    def check_organization_existence(self) -> None:
        """Check existence AWS organization."""
        self.client_org.describe_organization()

    def check_is_management_account(self) -> None:
        """Check if AWS API caller has same effective account ID as the organization's management account."""
        organization_info = self.client_org.describe_organization()
        iam_user_info = self.client_sts.get_caller_identity()

        management_account_id = organization_info["Organization"]["MasterAccountId"]
        api_caller_account_id = iam_user_info["Account"]
        is_management_account = management_account_id == api_caller_account_id

        if not is_management_account:
            raise Exception(f"AWS API caller and organization's management account have different account IDs.")

    def check_scp_enabled(self) -> None:
        """Check if SCP policy type feature is enabled for the AWS organization."""
        organization_info = self.client_org.describe_organization()
        available_policy_types = organization_info["AvailablePolicyTypes"]

        scp_is_enabled = any(
            policy["Type"] == "SERVICE_CONTROL_POLICY" and policy["Status"] == "ENABLED"
            for policy in available_policy_types
        )

        if not scp_is_enabled:
            raise Exception("The SCP policy type is disabled for the organization.")

    def pipeline_preconditions(self) -> None:
        """
        Check all crucial pipeline preconditions. Raises exception prematurely on failure.

        Preconditions:
        1. Locatable boto3 credentials and successful AWS API connection
        2. Check allowed AWS API actions based on IAM policy of caller
        3. Existing organization for AWS API caller
        4. AWS API caller acts under same account ID as organization's management account ID
        5. SCP policy type feature enabled for organization
        """
        preconditions = [
            (self.check_aws_api_connection, (), "AWS API connection established"),
            (self.check_iam_policy, (self.required_aws_actions), "AWS API actions permissions"),
            (self.check_organization_existence, (), "AWS organization existence"),
            (self.check_is_management_account, (), "AWS API caller is management account"),
            (self.check_scp_enabled, (), "SCP enabled"),
        ]

        for precondition, args, description in preconditions:
            precondition(*args)
            self.logger.info(f"Pipeline precondition success: {description}.")
