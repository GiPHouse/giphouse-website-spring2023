"""Framework for synchronisation with Amazon Web Services (AWS)."""

import json
import logging

import boto3

from botocore.exceptions import ClientError

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

    def __repr__(self):
        return f"{self.project_email}, {self.project_slug}, {self.project_semester}"


class Iteration:
    """
    Datatype for AWS data in the Course iteration OU
    """
    def __init__(self, name, id, members: list[SyncData]):
        self.name = name
        self.id = id
        self.members = members

    def __repr__(self):
        return f"Iteration({self.name}, {self.id}, {self.members})"

class AWSTree:
    """
    Tree structure for AWS data
    """
    def __init__(self, name, id, iterations: list[Iteration]):
        self.name = name
        self.id = id
        self.iterations = iterations

    def __repr__(self):
        return f"AWSTree({self.name}, {self.id}, {self.iterations})"

    def awstree_to_syncdata_list(self):
        """
        Converges AWSTree to list of SyncData elements.
        """
        awslist = []

        for interation in self.iterations:
            for member in interation.members:
                awslist.append(member)

        return awslist

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
            project_semester = str(Semester.objects.get(pk=project["semester"])
                                   )
            project_email = MailingList.objects.get(pk=project["mailinglist"])\
                .email_address

            sync_data = SyncData(project_email, project_slug, project_semester)
            email_ids.append(sync_data)
        return email_ids

    def create_aws_organization(self):
        """Create an AWS organization with the current user as the management account."""
        client = boto3.client("organizations")
        try:
            response = client.create_organization(FeatureSet="ALL")
            self.org_info = response["Organization"]
            self.logger.info("Created an AWS organization and saved \
                              organization info.")
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong creating an \
                               AWS organization.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def generate_aws_sync_list(self, giphouse_data, aws_data):
        """
        Generate the list of users that are registered on the GiPhouse website,
          but are not yet invited for AWS.

        This includes their ID and email address, to be able to put users in 
            the correct AWS orginization later.
        """
        sync_list = [x for x in giphouse_data if x not in aws_data]
        return sync_list

    def create_scp_policy(self, policy_name, policy_description, 
                          policy_content):
        """
        Create a SCP policy.

        :param policy_name: The policy name.
        :param policy_description: The policy description.
        :param policy_content: The policy configuration as a dictionary. 
        The policy is automatically converted to JSON format, including 
            escaped quotation marks.
        :return: Details of newly created policy as a dict on success 
            and NoneType object otherwise.
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
        Attaches a SCP policy to a target (root, OU, or member account).

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

    def extract_aws_setup(self, parent_ou_id):
        """
        Gives a list of all the children of the parent OU.

        :param parent_ou_id: The ID of the root ID.
        """
        client = boto3.client("organizations")
        try:
            response = client.list_organizational_units_for_parent(ParentId=parent_ou_id)
            aws_tree = AWSTree("root", parent_ou_id, [])
            for iteration in response["OrganizationalUnits"]:
                ou_id = iteration["Id"]
                ou_name = iteration["Name"]
                response = client.list_accounts_for_parent(ParentId=ou_id)
                children = response["Accounts"]
                syncData = []
                for child in children:
                    account_id = child["Id"]
                    account_email = child["Email"]
                    response = client.list_tags_for_resource(ResourceId=account_id)
                    tags = response['Tags']
                    merged_tags = {d["Key"]: d["Value"] for d in tags}
                    self.logger.debug(merged_tags)
                    if all(key in merged_tags for key in ["project_slug",
                                                          "project_semester"]):
                        syncData.append(SyncData(account_email,
                                                 merged_tags["project_slug"],
                                                 merged_tags["project_semester"]))
                    else:
                        self.logger.error("Could not find project_slug or project_semester tag for account with ID: " + account_id)
                        self.fail = True

                aws_tree.iterations.append(Iteration(ou_name, ou_id, syncData))
            return aws_tree
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong extracting the AWS setup.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

