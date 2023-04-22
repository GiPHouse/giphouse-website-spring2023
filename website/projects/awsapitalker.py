import boto3


class AWSAPITalker:
    """Communicate with AWS boto3 API."""

    def __init__(self):
        """Initialize the clients needed to communicate with the boto3 API."""
        self.iam_client = boto3.client("iam")
        self.org_client = boto3.client("organizations")
        self.sts_client = boto3.client("sts")

    def create_organization(self, feature_set : str) -> dict:
        """
        Create an AWS organization.

        :param feature_set: enabled features in the organization (either 'ALL' or 'CONSOLIDATED BILLING').
        :return: dictionary containing information about the organization.
        """
        return self.org_client.create_organization(FeatureSet=feature_set)

    def create_organizational_unit(self, parent_id : str, ou_name : str, tags : list[dict] = []) -> dict:
        """
        Create an organizational unit.

        :param parent_id: parent OU ID define where you want to create the new OU.
        :param ou_name: ou_name deifne the name of the new OU.
        :param tags: tags (list of dictionaries containing the keys 'Key' and 'Value') to be attached to the account.
        :return: dictionary containing information about the organizational unit.
        """
        return self.org_client.create_organizational_unit(
            ParentId=parent_id,
            Name=ou_name,
            Tags=tags
        )

    def attach_policy(self, target_id : str, policy_id : str):
        """
        Attach the specified policy to the specified target.

        :param target_id: string target_id is identifying the target.
        :param policy_id:string policy_id is identifying the policy.
        """
        self.org_client.attach_policy(
            TargetId=target_id,
            PolicyId=policy_id
        )

    def get_caller_identity(self) -> dict:
        """Get the identity of the caller of the API actions."""
        return self.sts_client.get_caller_identity()

    def simulate_principal_policy(self, policy_source_arn : str, action_names : list[str]) -> dict:
        """
        Determine the effective permissions of the policies of an IAM entity by simulating API actions.

        :param policy_source: ARN of the IAM entity.
        :param action_names: list of AWS API actions to simulate.
        :return: dictionary containing information about the simulation's outcome.
        """
        return self.iam_client.simulate_principal_policy(
            PolicySourceArn=policy_source_arn,
            ActionNames=action_names
        )

    def describe_organization(self) -> dict:
        """Describe the AWS organization."""
        return self.org_client.describe_organization()

    def describe_policy(self, policy_id : str) -> dict:
        """Describe the policy with the specified ID."""
        return self.org_client.describe_policy(PolicyId=policy_id)

    def create_account(self, email : str, account_name : str, tags : list[dict] = []) -> dict:
        """
        Move an AWS account in the organization.

        :param email: email address of the account.
        :param account_name: name of the account.
        :param tags: tags (list of dictionaries containing the keys 'Key' and 'Value') to be attached to the account.
        :return: dictionary containing information about the account creation status.
        """
        return self.org_client.create_account(
            Email=email,
            AccountName=account_name,
            IamUserAccessToBilling="DENY",
            Tags=tags
        )

    def move_account(self, account_id : str, source_parent_id : str, dest_parent_id : str):
        """
        Move an AWS account in the organization.

        :param account_id: ID of the account.
        :param source_parent_id: ID of the root/OU containing the account.
        :param dest_parent_id: ID of the root/OU which the account should be moved to.
        """
        self.org_client.move_account(
            AccountId=account_id,
            SourceParentId=source_parent_id,
            DestinationParentId=dest_parent_id
        )
