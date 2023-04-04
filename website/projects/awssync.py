"""Framework for synchronisation with Amazon Web Services (AWS)."""

import json
import logging

import boto3

from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError

from courses.models import Semester

from mailing_lists.models import MailingList

from projects.models import Project


class SyncData:
    """Structure for AWS giphouse sync data."""

    def __init__(self, project_email, project_slug, project_semester):
        """Create SyncData instance."""
        self.project_email = project_email
        self.project_slug = project_slug
        self.project_semester = project_semester

    def __eq__(self, other):
        """Overload equals for SyncData type."""
        if not isinstance(other, SyncData):
            raise TypeError("Must compare to object of type SyncData")
        return (
            self.project_email == other.project_email
            and self.project_slug == other.project_slug
            and self.project_semester == other.project_semester
        )


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)
        self.org_info = None
        self.fail = False
        self.logger.info("Created AWSSync instance.")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        self.logger.info("Pressed button")
        self.logger.info(self.get_emails_with_teamids())
        self.logger.debug(f"Pipeline check result: {self.pipeline_preconditions()}")

        return True

    def get_all_mailing_lists(self):
        """
        Get all mailing lists from the database.

        :return: List of mailing lists
        """
        mailing_lists = MailingList.objects.all()
        mailing_list_names = [ml.email_address for ml in mailing_lists]
        return mailing_list_names

    def get_emails_with_teamids(self):
        """
        Create a list of SyncData struct containing email, slug and semester.

        Slug and semester combined are together an uniqueness constraint.

        :return: list of SyncData structs with email, slug and semester
        """
        email_ids = []

        for project in (
            Project.objects.filter(mailinglist__isnull=False)
            .filter(semester=Semester.objects.get_or_create_current_semester())
            .values("slug", "semester", "mailinglist")
        ):
            project_slug = project["slug"]
            project_semester = str(Semester.objects.get(pk=project["semester"]))
            project_email = MailingList.objects.get(pk=project["mailinglist"]).email_address

            sync_data = SyncData(project_email, project_slug, project_semester)
            email_ids.append(sync_data)
        return email_ids

    def create_aws_organization(self):
        """Create an AWS organization with the current user as the management account."""
        client = boto3.client("organizations")
        try:
            response = client.create_organization(FeatureSet="ALL")
            self.org_info = response["Organization"]
            self.logger.info("Created an AWS organization and saved organization info.")
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong creating an AWS organization.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def generate_aws_sync_list(self, giphouse_data, aws_data):
        """
        Generate the list of users that are registered on the GiPhouse website, but are not yet invited for AWS.

        This includes their ID and email address, to be able to put users in the correct AWS orginization later.
        """
        sync_list = [x for x in giphouse_data if x not in aws_data]
        return sync_list

    def create_scp_policy(self, policy_name, policy_description, policy_content):
        """
        Create an SCP policy.

        :param policy_name: The policy name.
        :param policy_description: The policy description.
        :param policy_content: The policy configuration as a dictionary. The policy is automatically
                               converted to JSON format, including escaped quotation marks.
        :return: Details of newly created policy as a dict on success and NoneType object otherwise.
        """
        client = boto3.client("organizations")
        try:
            response = client.create_policy(
                Content=json.dumps(policy_content),
                Description=policy_description,
                Name=policy_name,
                Type="SERVICE_CONTROL_POLICY",
            )
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong creating an SCP policy.")
            self.logger.error(error)
        else:
            return response["Policy"]

    def attach_scp_policy(self, policy_id, target_id):
        """
        Attaches an SCP policy to a target (root, OU, or member account).

        :param policy_id: The ID of the policy to be attached.
        :param target_id: The ID of the target root, OU, or member account.
        """
        client = boto3.client("organizations")
        try:
            client.attach_policy(PolicyId=policy_id, TargetId=target_id)
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong attaching an SCP policy to a target.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def check_aws_api_connection(self):
        """
        Check whether boto3 can connect to AWS API with current credentials.

        :returns: First tuple element always exists and indicates success.
                  Second tuple element is contains information about the entity
                  who made the successful API call and None otherwise.
        """
        client_sts = boto3.client("sts")
        try:
            caller_identity_info = client_sts.get_caller_identity()
        except (NoCredentialsError, ClientError) as error:
            self.logger.info("Establishing AWS API connection failed.")
            self.logger.debug(error)
            return False, None
        else:
            self.logger.info("Establishing AWS API connection succeeded.")

        return True, caller_identity_info

    def check_organization_existence(self):
        """
        Check whether an AWS organization exists for the AWS API caller's account.

        :returns: First tuple element always exists and indicates success.
                  Second tuple element is describes properties of the organization and None otherwise.
        """
        client_organizations = boto3.client("organizations")

        try:
            response_org = client_organizations.describe_organization()
        except ClientError as error:
            self.logger.info("AWS organization existence check failed.")
            self.logger.debug(error)
            return False, None
        else:
            self.logger.info("AWS organization existence check succeeded.")

        return True, response_org["Organization"]

    def check_is_management_account(self, api_caller_info, organization_info):
        """
        Check whether caller of AWS API has organization's management account ID.

        :returns: True iff the current organization's management account ID equals the AWS API caller's account ID.
        """
        management_account_id = organization_info["MasterAccountId"]
        api_caller_account_id = api_caller_info["Account"]
        is_management_account = management_account_id == api_caller_account_id

        if is_management_account:
            self.logger.info("Management account check succeeded.")
        else:
            self.logger.info("Management account check failed.")
            self.logger.debug(f"The organization's management account ID is: '{management_account_id}'.")
            self.logger.debug(f"The AWS API caller account ID is:            '{api_caller_account_id}'.")

        return is_management_account

    def check_scp_enabled(self, organization_info):
        """
        Check whether the SCP policy type is an enabled feature for the AWS organization.

        :returns: True iff the SCP policy type feature is enabled for the organization.
        """
        scp_is_enabled = False
        for policy in organization_info["AvailablePolicyTypes"]:
            if policy["Type"] == "SERVICE_CONTROL_POLICY" and policy["Status"] == "ENABLED":
                scp_is_enabled = True
                break

        if not scp_is_enabled:
            self.logger.info("The SCP policy type is disabled for the organization.")
            self.logger.debug(organization_info["AvailablePolicyTypes"])
        else:
            self.logger.info("Organization SCP policy status check succeeded.")

        return scp_is_enabled

    def pipeline_preconditions(self):
        """
        Check all crucial pipeline preconditions.

        1. Locatable boto3 credentials and successful AWS API connection
        2. Existing organization for AWS API caller
        3. AWS API caller acts under same account ID as organization's management account ID
        4. SCP policy type feature enabled for organization

        :return: True iff all pipeline preconditions are met.
        """
        check_api_connection, api_caller_info = self.check_aws_api_connection()
        if not check_api_connection:
            return False

        check_org_existence, organization_info = self.check_organization_existence()
        if not check_org_existence:
            return False

        check_acc_management = self.check_is_management_account(api_caller_info, organization_info)
        if not check_acc_management:
            return False

        check_scp_enabled = self.check_scp_enabled(organization_info)
        if not check_scp_enabled:
            return False

        return True

    def pipeline(self):
        """
        Single pipeline that integrates all buildings blocks for the AWS integration process.

        :return: True iff all pipeline stages successfully executed.
        """
        # 1058274
        self.logger.info("Starting pipeline preconditions check.")
        if not self.pipeline_preconditions():
            self.logger.info("Failed pipeline preconditions check.")
            return False
        self.logger.info("All pipeline preconditions passed.")

        # hb140502
        # Jer111
        return True
