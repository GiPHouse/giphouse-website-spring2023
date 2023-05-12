from __future__ import annotations

import logging

import boto3

from botocore.exceptions import ClientError

from courses.models import Semester

from mailing_lists.models import MailingList

from projects.aws.awsapitalker import AWSAPITalker
from projects.aws.awssync_structs import AWSTree, Iteration, SyncData
from projects.models import Project


class AWSSyncRefactored:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.api_talker = AWSAPITalker()
        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)
        self.org_info = None
        self.fail = False

    def get_all_mailing_lists(self) -> list[str]:
        """
        Get all mailing lists from the database.

        :return: List of mailing list email addresses.
        """
        mailing_lists = MailingList.objects.all()
        mailing_list_names = [ml.email_address for ml in mailing_lists]
        return mailing_list_names

    def get_syncdata_from_giphouse(self) -> list[SyncData]:
        """
        Create a list of SyncData struct containing email, slug and semester.

        Slug and semester combined are together an uniqueness constraint.

        :return: list of SyncData structs with email, slug and semester
        """
        sync_data_list = []
        current_semester = Semester.objects.get_or_create_current_semester()

        for project in Project.objects.filter(mailinglist__isnull=False, semester=current_semester).values(
            "slug", "semester", "mailinglist"
        ):
            project_slug = project["slug"]
            project_semester = str(Semester.objects.get(pk=project["semester"]))
            project_email = MailingList.objects.get(pk=project["mailinglist"]).email_address

            sync_data = SyncData(project_email, project_slug, project_semester)
            sync_data_list.append(sync_data)
        return sync_data_list

    def generate_aws_sync_list(self, giphouse_data: list[SyncData], aws_data: list[SyncData]) -> list[SyncData]:
        """
        Generate the list of users that are registered on the GiPhouse website, but are not yet invited for AWS.

        This includes their ID and email address, to be able to put users in the correct AWS organization later.
        """
        return [x for x in giphouse_data if x not in aws_data]

    def extract_aws_setup(self, parent_ou_id: str) -> AWSTree:
        """
        Give a list of all the children of the parent OU.

        :param parent_ou_id: The ID of the parent OU.
        :return: A AWSTree object containing all the children of the parent OU.
        """
        try:
            OUs_for_parent = self.api_talker.list_organizational_units_for_parent(parent_id=parent_ou_id)
            aws_tree = AWSTree("root", parent_ou_id, [])
            for ou in OUs_for_parent:
                accounts = self.api_talker.list_accounts_for_parent(parent_id=ou["Id"])
                sync_data = []
                for account in accounts:
                    tags = {
                        d["Key"]: d["Value"] for d in self.api_talker.list_tags_for_resource(resource_id=account["Id"])
                    }
                    if all(key in tags for key in ["project_slug", "project_semester"]):
                        sync_data.append(SyncData(account["Email"], tags["project_slug"], tags["project_semester"]))
                    else:
                        self.logger.error(
                            f"Could not find project_slug or project_semester tag for account with ID: {account['Id']}"
                        )
                        self.fail = True

                aws_tree.iterations.append(Iteration(ou["Name"], ou["Id"], sync_data))
            return aws_tree
        except ClientError as error:
            self.logger.error(f"Something went wrong extracting the AWS setup: {error}")
            self.fail = True

    def get_or_create_course_ou(self, tree: AWSTree) -> str:
        """Create organizational unit under root with name of current semester."""
        root_id = tree.ou_id
        course_ou_name = str(Semester.objects.get_or_create_current_semester())
        course_ou_id = next((ou.ou_id for ou in tree.iterations if ou.name == course_ou_name), None)

        if not course_ou_id:
            course_ou = self.api_talker.create_organizational_unit(root_id, course_ou_name)
            course_ou_id = course_ou["OrganizationalUnit"]["Id"]

        return course_ou_id

    def attach_policy(self, target_id: str, policy_id: str) -> None:
        """Attach policy to target resource."""
        try:
            self.api_talker.attach_policy(target_id, policy_id)
        except ClientError as error:
            if error.response["Error"]["Code"] != "DuplicatePolicyAttachmentException":
                raise
